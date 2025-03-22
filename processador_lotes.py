from flask import Flask, jsonify
import aiohttp
import asyncio
import logging
import math  # Adicionando a importação do módulo math
from typing import List, Dict, Any
import time

# Configuração do logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ProcessadorLotes")

class ProcessadorLotes:
    def __init__(self, tamanho_lote: int = 930, max_concurrent: int = 5):
        """
        Inicializa o processador de lotes
        
        Args:
            tamanho_lote: Tamanho de cada lote (padrão: 930)
            max_concurrent: Número máximo de requisições simultâneas (padrão: 5)
        """
        self.tamanho_lote = tamanho_lote
        self.max_concurrent = max_concurrent
        self.session = None
        self.api_base_url = "https://loteriascaixa-api.herokuapp.com/api"
    
    async def __aenter__(self):
        """Inicializa a sessão HTTP"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Fecha a sessão HTTP"""
        if self.session:
            await self.session.close()
    
    async def buscar_com_retry(self, concurso: int, max_tentativas: int = 3) -> Dict:
        """
        Busca um resultado específico com tentativas em caso de falha
        
        Args:
            concurso: Número do concurso
            max_tentativas: Número máximo de tentativas
            
        Returns:
            Dict com o resultado ou None em caso de falha
        """
        for tentativa in range(max_tentativas):
            try:
                # Tenta obter do cache primeiro
                from redis_config import redis_config
                cached = redis_config.get_cached_result(concurso)
                if cached:
                    logger.debug(f"Concurso {concurso} obtido do cache.")
                    return cached
                    
                # Se não estiver em cache, busca da API
                async with self.session.get(
                    f"{self.api_base_url}/diadesorte/{concurso}",
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        try:
                            resultado = await response.json()
                            if resultado:
                                # Verificar se o resultado tem os campos esperados
                                if 'dezenas' in resultado or 'listaDezenas' in resultado:
                                    # Normaliza o resultado
                                    if 'dezenas' in resultado:
                                        # Formato da API principal
                                        dezenas = resultado.get('dezenas', [])
                                        mes_sorte = resultado.get('mesDaSorte', '')
                                    elif 'listaDezenas' in resultado:
                                        # Formato da API alternativa
                                        dezenas = resultado.get('listaDezenas', [])
                                        mes_sorte = resultado.get('nomeTimeCoracaoMesSorte', '')
                                    else:
                                        logger.error(f"Formato de resultado desconhecido para concurso {concurso}")
                                        await asyncio.sleep(2 ** tentativa)
                                        continue
                                        
                                    redis_config.set_cached_result(concurso, resultado)
                                    return resultado
                                else:
                                    logger.error(f"Resultado incompleto para concurso {concurso}")
                            else:
                                logger.error(f"Resultado vazio para concurso {concurso}")
                        except Exception as e:
                            logger.error(f"Erro ao processar resposta para concurso {concurso}: {str(e)}")
                            
                    logger.warning(f"Resposta inválida para concurso {concurso}, status: {response.status}")
                    await asyncio.sleep(2 ** tentativa)  # Backoff exponencial
                    continue
                    
            except aiohttp.ClientError as e:
                logger.error(f"Erro de rede ao buscar concurso {concurso}: {str(e)}")
            except asyncio.TimeoutError:
                logger.error(f"Timeout ao buscar concurso {concurso}")
            except Exception as e:
                logger.error(f"Erro desconhecido ao buscar concurso {concurso}: {str(e)}")
                
            if tentativa < max_tentativas - 1:
                await asyncio.sleep(2 ** tentativa)  # Backoff exponencial
            else:
                logger.error(f"Todas as tentativas falharam para concurso {concurso}")
                
        return None

    async def processar_lote(self, inicio: int, fim: int, jogos: List[Dict]) -> List[Dict]:
        """
        Processa um lote de resultados
        
        Args:
            inicio: Número do primeiro concurso
            fim: Número do último concurso
            jogos: Lista de jogos para conferir
            
        Returns:
            Lista de resultados processados
        """
        tarefas = []
        resultados = []
        
        # Cria tarefas para busca concorrente
        for concurso in range(inicio, min(fim + 1, inicio + self.tamanho_lote)):
            tarefa = asyncio.create_task(self.buscar_com_retry(concurso))
            tarefas.append((concurso, tarefa))
            
            # Se atingiu o máximo de tarefas concorrentes, espera algumas completarem
            if len(tarefas) >= self.max_concurrent:
                completadas = await self.processar_chunk_tarefas(tarefas[:self.max_concurrent], jogos)
                resultados.extend(completadas)
                tarefas = tarefas[self.max_concurrent:]
        
        # Processa tarefas restantes
        if tarefas:
            completadas = await self.processar_chunk_tarefas(tarefas, jogos)
            resultados.extend(completadas)
        
        return resultados

    async def processar_chunk_tarefas(self, tarefas: List[tuple], jogos: List[Dict]) -> List[Dict]:
        """
        Processa um conjunto de tarefas e confere contra os jogos
        
        Args:
            tarefas: Lista de tuplas (concurso, tarefa)
            jogos: Lista de jogos para conferir
            
        Returns:
            Lista de resultados processados
        """
        resultados = []
        for concurso, tarefa in tarefas:
            try:
                resultado = await tarefa
                if resultado and 'dezenas' in resultado:
                    # Processa cada jogo contra este resultado
                    resultados_processados = self.conferir_jogos_contra_resultado(jogos, resultado)
                    resultados.extend(resultados_processados)
            except Exception as e:
                logger.error(f"Erro processando concurso {concurso}: {str(e)}")
        return resultados

    def conferir_jogos_contra_resultado(self, jogos: List[Dict], resultado: Dict) -> List[Dict]:
        """
        Confere jogos contra um resultado específico
        
        Args:
            jogos: Lista de jogos para conferir
            resultado: Resultado do concurso
            
        Returns:
            Lista de acertos encontrados
        """
        acertos = []
        # Normaliza a estrutura do resultado para suportar múltiplas APIs
        dezenas = [int(d) for d in resultado.get('dezenas', [])]
        mes_sorteado = resultado.get('mesDaSorte', '')
        
        # Se estiver usando a API alternativa, o mês pode estar em outro campo
        if not mes_sorteado and 'nomeTimeCoracaoMesSorte' in resultado:
            mes_sorteado = resultado['nomeTimeCoracaoMesSorte']
        
        if mes_sorteado:
            mes_sorteado = mes_sorteado.upper()
        
        for jogo in jogos:
            numeros = jogo['numeros']
            mes_jogado = jogo.get('mes', '').upper() if jogo.get('mes') else None
            
            acertos_numeros = len(set(numeros) & set(dezenas))
            acertou_mes = mes_jogado and mes_sorteado and mes_jogado == mes_sorteado
            
            if acertos_numeros >= 4 or acertou_mes:
                premio = self.calcular_premio(resultado, acertos_numeros, acertou_mes)
                acertos.append({
                    'concurso': resultado.get('concurso'),
                    'data': resultado.get('data'),
                    'numeros_sorteados': dezenas,
                    'mes_sorteado': mes_sorteado,
                    'seus_numeros': numeros,
                    'seu_mes': mes_jogado,
                    'acertos': acertos_numeros,
                    'acertou_mes': acertou_mes,
                    'premio': premio
                })
                
        return acertos

    def calcular_premio(self, resultado: Dict, acertos: int, acertou_mes: bool = False) -> float:
        """
        Calcula o prêmio baseado nos acertos
        
        Args:
            resultado: Resultado do concurso
            acertos: Número de acertos
            acertou_mes: Se acertou o mês
            
        Returns:
            Valor do prêmio
        """
        premio = 0
        if 'premiacoes' in resultado:
            for premiacao in resultado['premiacoes']:
                if ((acertos == 7 and premiacao['descricao'] == '7 acertos') or
                    (acertos == 6 and premiacao['descricao'] == '6 acertos') or
                    (acertos == 5 and premiacao['descricao'] == '5 acertos') or
                    (acertos == 4 and premiacao['descricao'] == '4 acertos') or
                    (acertou_mes and premiacao['descricao'] == 'Mês da Sorte')):
                    premio += premiacao['valorPremio']
        return premio

async def processar_todos_jogos(inicio: int, fim: int, jogos: List[Dict]) -> Dict:
    """
    Processa todos os jogos em lotes
    
    Args:
        inicio: Primeiro concurso
        fim: Último concurso
        jogos: Lista de jogos para conferir
        
    Returns:
        Dicionário com resultados e estatísticas
    """
    try:
        async with ProcessadorLotes() as processador:
            todos_resultados = []
            total_lotes = math.ceil((fim - inicio + 1) / processador.tamanho_lote)
            
            for i in range(inicio, fim + 1, processador.tamanho_lote):
                lote_atual = (i - inicio) // processador.tamanho_lote + 1
                lote_fim = min(i + processador.tamanho_lote - 1, fim)
                
                logger.info(f"Processando lote {lote_atual} de {total_lotes}: concursos {i} até {lote_fim}")
                
                try:
                    resultados_lote = await processador.processar_lote(i, lote_fim, jogos)
                    todos_resultados.extend(resultados_lote)
                except Exception as e:
                    logger.error(f"Erro no processamento do lote {lote_atual}: {str(e)}")
                    logger.error(f"Tentando continuar com o próximo lote...")
                    await asyncio.sleep(2)  # Pausa mais longa antes de tentar o próximo lote
                    continue
                
                # Pequena pausa entre lotes para evitar sobrecarga
                await asyncio.sleep(0.5)
            
            # Se não conseguimos processar nenhum resultado, levanta uma exceção
            if not todos_resultados and total_lotes > 0:
                raise Exception("Não foi possível processar nenhum resultado nos lotes de concursos.")
                
            logger.info("Processamento de todos os lotes concluído com sucesso!")
            
            # Adicione log para informações de resumo
            resumo = calcular_resumo(todos_resultados)
            logger.info(f"Resumo de resultados: acertos 4: {resumo['quatro']}, 5: {resumo['cinco']}, 6: {resumo['seis']}, 7: {resumo['sete']}, mês: {resumo['mes']}")
            
            return {
                'acertos': todos_resultados,
                'resumo': resumo,
                'jogos_stats': calcular_estatisticas_jogos(todos_resultados, jogos)
            }
    except Exception as e:
        logger.error(f"Erro no processamento geral: {str(e)}")
        raise Exception(f"Erro ao processar os lotes de concursos: {str(e)}")

def calcular_resumo(resultados: List[Dict]) -> Dict:
    """
    Calcula o resumo dos resultados
    
    Args:
        resultados: Lista de resultados
        
    Returns:
        Dicionário com resumo dos acertos e prêmios
    """
    return {
        'quatro': sum(1 for r in resultados if r['acertos'] == 4),
        'cinco': sum(1 for r in resultados if r['acertos'] == 5),
        'seis': sum(1 for r in resultados if r['acertos'] == 6),
        'sete': sum(1 for r in resultados if r['acertos'] == 7),
        'mes': sum(1 for r in resultados if r['acertou_mes']),
        'total_premios': sum(r['premio'] for r in resultados)
    }

def calcular_estatisticas_jogos(resultados: List[Dict], jogos: List[Dict]) -> List[Dict]:
    """
    Calcula estatísticas para cada jogo
    
    Args:
        resultados: Lista de resultados
        jogos: Lista de jogos
        
    Returns:
        Lista com estatísticas de cada jogo
    """
    jogos_stats = {}
    
    # Mapear todos os resultados dos concursos
    for resultado in resultados:
        concurso = resultado['concurso']
        numeros_sorteados = resultado['numeros_sorteados']
        mes_sorteado = resultado.get('mes_sorteado', '')
        
        # Para cada jogo do usuário, calcular acertos neste concurso
        for jogo in jogos:
            numeros_jogo = tuple(sorted(jogo['numeros']))
            mes_jogo = jogo.get('mes', '')
            
            # Criar entrada para este jogo se não existir
            if numeros_jogo not in jogos_stats:
                jogos_stats[numeros_jogo] = {
                    'numeros': list(numeros_jogo),
                    'total': 0,
                    'distribuicao': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0},
                    'acertos_mes': 0
                }
            
            # Calcular acertos para este jogo neste concurso
            acertos = len(set(numeros_jogo) & set(numeros_sorteados))
            acertou_mes = mes_jogo and mes_sorteado and mes_jogo.upper() == mes_sorteado.upper()
            
            # Atualizar estatísticas
            if acertos > 0:
                jogos_stats[numeros_jogo]['total'] += 1
                jogos_stats[numeros_jogo]['distribuicao'][acertos] += 1
            
            if acertou_mes:
                jogos_stats[numeros_jogo]['acertos_mes'] += 1
    
    # Converter de dicionário para lista e ordenar por total de acertos (decrescente)
    resultado_final = list(jogos_stats.values())
    resultado_final.sort(key=lambda x: x['total'], reverse=True)
    
    return resultado_final