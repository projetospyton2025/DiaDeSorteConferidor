from flask import Flask, jsonify
import aiohttp
import asyncio
import logging
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
                async with self.session.get(
                    f"{self.api_base_url}/diadesorte/{concurso}",
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Tentativa {tentativa + 1} falhou para concurso {concurso}: {str(e)}")
                if tentativa == max_tentativas - 1:
                    return None
                await asyncio.sleep(2 ** tentativa)
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
        dezenas = [int(d) for d in resultado['dezenas']]
        mes_sorteado = resultado.get('mesDaSorte', '').upper()
        
        for jogo in jogos:
            numeros = jogo['numeros']
            mes_jogado = jogo.get('mes', '').upper() if jogo.get('mes') else None
            
            acertos_numeros = len(set(numeros) & set(dezenas))
            acertou_mes = mes_jogado and mes_jogado == mes_sorteado
            
            if acertos_numeros >= 4 or acertou_mes:
                premio = self.calcular_premio(resultado, acertos_numeros, acertou_mes)
                acertos.append({
                    'concurso': resultado['concurso'],
                    'data': resultado['data'],
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
    async with ProcessadorLotes() as processador:
        todos_resultados = []
        for i in range(inicio, fim + 1, processador.tamanho_lote):
            lote_fim = min(i + processador.tamanho_lote - 1, fim)
            logger.info(f"Processando lote de concursos {i} até {lote_fim}")
            
            resultados_lote = await processador.processar_lote(i, lote_fim, jogos)
            todos_resultados.extend(resultados_lote)
            
            # Pequena pausa entre lotes para evitar sobrecarga
            await asyncio.sleep(1)
        
        return {
            'acertos': todos_resultados,
            'resumo': calcular_resumo(todos_resultados)
        }

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