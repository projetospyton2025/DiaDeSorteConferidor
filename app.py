from flask import Flask, render_template, request, jsonify, send_file
from processador_lotes import processar_todos_jogos
from redis_config import redis_config
from datetime import datetime
from dotenv import load_dotenv
import logging
import random
import aiohttp
import asyncio
import json
import pandas as pd
import io
import os

# Configurações globais para controle de requisições e processamento
CONCURRENT_REQUESTS = 5  # Número máximo de requisições simultâneas
BATCH_SIZE = 930        # Tamanho do lote de concursos
RETRY_ATTEMPTS = 3      # Número de tentativas para cada requisição
BASE_DELAY = 1         # Delay base em segundos para retry
API_BASE_URL = "https://loteriascaixa-api.herokuapp.com/api"  # API principal
# API_BASE_URL = "https://servicebus2.caixa.gov.br/portaldeloterias/api/diadesorte"  # API alternativa (comentada)

# Configurações do Flask
FLASK_RUN_TIMEOUT = 900  # 15 minutos
CHUNK_SIZE = 1000        # Reduzido de 5000 para 1000
CONCURSOS_PER_BATCH = 930  # Manter atual divisão de concursos
MAX_CONCURRENT_REQUESTS = 5  # Reduzido de 10 para 5

# Configuração de logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Dia de Sorte Conferidor")


# Carregar variáveis do .env
load_dotenv()

app = Flask(__name__)

# Lista de meses para o Dia de Sorte
MESES = [
    "JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO",
    "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"
]

async def fetch_with_retry(session, url, max_retries=3):
    timeout = aiohttp.ClientTimeout(total=30)
    for attempt in range(max_retries):
        try:
            async with session.get(url, timeout=timeout) as response:
                if response.status == 200:
                    return await response.json()
                await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Tentativa {attempt + 1} falhou: {str(e)}")
            if attempt == max_retries - 1:
                return None
            await asyncio.sleep(2 ** attempt)
    return None

async def get_latest_result():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE_URL}/diadesorte/latest") as response:
                if response.status == 200:
                    return await response.json()
                return None
    except Exception as e:
        logger.error(f"Erro ao buscar último resultado: {str(e)}")
        return None

@app.route('/')
async def index():
    latest = await get_latest_result()
    ultimo_concurso = latest['concurso'] if latest else 500  # valor padrão para Dia de Sorte
    return render_template('index.html', ultimo_concurso=ultimo_concurso, meses=MESES)

@app.route('/gerar_numeros')
async def gerar_numeros():
    numeros = random.sample(range(1, 32), 7)  # 7 números de 1 a 31
    mes = random.choice(MESES)
    return jsonify({'numeros': sorted(numeros), 'mes': mes})

@app.route('/processar_arquivo', methods=['POST'])
def processar_arquivo():
    if 'file' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Nenhum arquivo selecionado'}), 400

    try:
        jogos = []
        logger.info(f"Processando arquivo: {file.filename}")
        
        if file.filename.endswith('.txt'):
            try:
                content = file.read().decode('utf-8-sig')
                for line in content.strip().split('\n'):
                    try:
                        line = ''.join(c for c in line if c.isdigit() or c.isspace())
                        numbers = [int(n) for n in line.strip().split()]
                        if len(numbers) == 7 and all(1 <= n <= 31 for n in numbers) and len(set(numbers)) == 7:
                            jogos.append({'numeros': sorted(numbers), 'mes': None})
                    except Exception as e:
                        logger.error(f"Erro na linha: {str(e)}")
                        continue
            except Exception as e:
                logger.error(f"Erro no TXT: {str(e)}")
                
        elif file.filename.endswith(('.xlsx', '.xls')):
            try:
                df = pd.read_excel(file)
                for _, row in df.iterrows():
                    numbers = []
                    for val in row.values[:7]:  # Primeiros 7 valores para números
                        try:
                            num = int(float(val))
                            if 1 <= num <= 31:
                                numbers.append(num)
                        except:
                            continue
                    if len(numbers) == 7 and len(set(numbers)) == 7:
                        mes = None
                        if len(row) > 7:  # Se houver coluna para mês
                            try:
                                mes = str(row.values[7]).upper()
                                if mes not in MESES:
                                    mes = None
                            except:
                                mes = None
                        jogos.append({'numeros': sorted(numbers), 'mes': mes})
            except Exception as e:
                logger.error(f"Erro no Excel: {str(e)}")
        else:
            return jsonify({'error': 'Use .txt ou .xlsx'}), 400

        if not jogos:
            return jsonify({'error': 'Nenhum jogo válido encontrado'}), 400

        logger.info(f"Jogos processados: {len(jogos)}")
        return jsonify({'jogos': jogos})

    except Exception as e:
        logger.error(f"Erro geral: {str(e)}")
        return jsonify({'error': f'Erro ao processar arquivo: {str(e)}'}), 500
        
@app.route('/conferir', methods=['POST'])
async def conferir():
    try:
        data = request.get_json()
        jogos = data['jogos']
        
<<<<<<< HEAD
        # Pega os números dos concursos
        inicio = int(data.get('inicio', 1))
        fim = int(data.get('fim', await obter_ultimo_concurso()))
=======
        logger.info(f"\n{'='*50}")
        logger.info(f"Iniciando conferência com {len(jogos)} jogos")
        logger.info("Detalhes dos jogos a serem conferidos:")
        for idx, jogo in enumerate(jogos, 1):
            numeros_formatados = ', '.join(str(n).zfill(2) for n in sorted(jogo['numeros']))
            mes_info = f" | Mês: {jogo.get('mes', 'não informado')}" if jogo.get('mes') else ""
            logger.info(f"Jogo {idx}: [{numeros_formatados}]{mes_info}")
        logger.info(f"{'='*50}\n")
        
        # Definição dos lotes de concursos
        inicio = data.get('inicio', 1)
        fim = data.get('fim', await obter_ultimo_concurso())
        logger.info(f"Faixa de concursos a verificar: {inicio} até {fim}")
        logger.info(f"Total de concursos a processar: {fim - inicio + 1}")
>>>>>>> 6c387e8c1b6502446e404627ad16ddaeea95fed6
        
        # Usa o novo processador em lotes
        resultados = await processar_todos_jogos(inicio, fim, jogos)
        return jsonify(resultados)
        
<<<<<<< HEAD
    except Exception as e:
        logger.error(f"Erro na conferência: {str(e)}")
        return jsonify({
            'error': 'Erro ao processar jogos',
            'message': str(e)
        }), 500
=======
        logger.info("Iniciando processamento dos concursos...")
        async with aiohttp.ClientSession() as session:
            concursos_processados = 0
            premios_encontrados = 0
            
            for concurso in range(inicio, fim + 1):
                try:
                    concursos_processados += 1
                    logger.info(f"\nProcessando concurso {concurso} ({concursos_processados}/{fim - inicio + 1})")
                    
                    resultado = await fetch_with_retry(session, f"{API_BASE_URL}/diadesorte/{concurso}")
                    
                    if resultado and 'dezenas' in resultado:
                        dezenas = [int(d) for d in resultado['dezenas']]
                        mes_sorteado = resultado.get('mesDaSorte', '').upper()
                        dezenas_formatadas = ', '.join(str(d).zfill(2) for d in sorted(dezenas))
                        logger.info(f"Números sorteados: [{dezenas_formatadas}] | Mês: {mes_sorteado}")
                        
                        premios_concurso = 0
                        for jogo in jogos:
                            numeros = jogo['numeros']
                            mes_jogado = jogo.get('mes')
                            
                            acertos = len(set(numeros) & set(dezenas))
                            acertou_mes = mes_jogado and mes_jogado.upper() == mes_sorteado
                            
                            if acertos >= 4 or acertou_mes:
                                premio = calcular_premio(resultado, acertos, acertou_mes)
                                premios_concurso += 1
                                premios_encontrados += 1
                                
                                numeros_formatados = ', '.join(str(n).zfill(2) for n in sorted(numeros))
                                logger.info(f"  ✓ Prêmio encontrado!")
                                logger.info(f"    Jogo: [{numeros_formatados}]")
                                logger.info(f"    Acertos: {acertos}")
                                if mes_jogado:
                                    logger.info(f"    Mês jogado: {mes_jogado} - {'✓ ACERTOU!' if acertou_mes else '✗ não acertou'}")
                                logger.info(f"    Prêmio: R$ {premio:.2f}")
                                
                                if acertos == 4: resultados_finais['resumo']['quatro'] += 1
                                elif acertos == 5: resultados_finais['resumo']['cinco'] += 1
                                elif acertos == 6: resultados_finais['resumo']['seis'] += 1
                                elif acertos == 7: resultados_finais['resumo']['sete'] += 1
                                if acertou_mes: resultados_finais['resumo']['mes'] += 1
                                
                                resultados_finais['resumo']['total_premios'] += premio
                                
                                resultados_finais['acertos'].append({
                                    'concurso': resultado['concurso'],
                                    'data': resultado['data'],
                                    'numeros_sorteados': dezenas,
                                    'mes_sorteado': mes_sorteado,
                                    'seus_numeros': numeros,
                                    'seu_mes': mes_jogado,
                                    'acertos': acertos,
                                    'acertou_mes': acertou_mes,
                                    'premio': premio
                                })
                        
                        if premios_concurso > 0:
                            logger.info(f"  Total de prêmios no concurso {concurso}: {premios_concurso}")
                
                except Exception as e:
                    logger.error(f"Erro processando concurso {concurso}: {str(e)}")
                    continue
                
                await asyncio.sleep(0.1)  # Pequena pausa entre requisições
        
        logger.info(f"\n{'='*50}")
        logger.info("Processamento concluído! Resumo final:")
        logger.info(f"Total de concursos processados: {concursos_processados}")
        logger.info(f"Total de prêmios encontrados: {premios_encontrados}")
        logger.info("\nDistribuição dos acertos:")
        logger.info(f"- 4 acertos: {resultados_finais['resumo']['quatro']}")
        logger.info(f"- 5 acertos: {resultados_finais['resumo']['cinco']}")
        logger.info(f"- 6 acertos: {resultados_finais['resumo']['seis']}")
        logger.info(f"- 7 acertos: {resultados_finais['resumo']['sete']}")
        logger.info(f"- Mês da Sorte: {resultados_finais['resumo']['mes']}")
        logger.info(f"\nTotal em prêmios: R$ {resultados_finais['resumo']['total_premios']:.2f}")
        logger.info(f"{'='*50}\n")
        
        return jsonify(resultados_finais)

    except Exception as e:
        logger.error(f"Erro na conferência geral: {str(e)}")
        return jsonify({'error': 'Erro ao processar jogos', 'message': str(e)}), 500       
        
        
>>>>>>> 6c387e8c1b6502446e404627ad16ddaeea95fed6

def calcular_premio(resultado, acertos, acertou_mes=False):
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

async def obter_ultimo_concurso():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE_URL}/diadesorte/latest") as response:
                if response.status ==200:
                    latest = await response.json()
                    return latest['concurso']
                return 500  # Valor padrão se falhar
    except Exception as e:
        logger.error(f"Erro ao buscar último concurso: {str(e)}")
        return 500  # Valor padrão

async def fetch_concurso_with_retry(session, concurso, max_retries=3, delay_base=1):
    for attempt in range(max_retries):
        try:
            cached = redis_config.get_cached_result(concurso)
            if cached:
                return cached

            async with session.get(f"{API_BASE_URL}/diadesorte/{concurso}") as response:
                if response.status == 200:
                    resultado = await response.json()
                    if resultado and 'dezenas' in resultado:
                        redis_config.set_cached_result(concurso, resultado)
                        return resultado
                
                # Se chegou aqui, a resposta não foi válida
                delay = delay_base * (2 ** attempt)  # Exponential backoff
                await asyncio.sleep(delay)
                continue
                
        except Exception as e:
            logger.error(f"Tentativa {attempt + 1} falhou para concurso {concurso}: {str(e)}")
            if attempt < max_retries - 1:
                delay = delay_base * (2 ** attempt)
                await asyncio.sleep(delay)
            else:
                logger.error(f"Todas as tentativas falharam para concurso {concurso}")
                return None
    return None

def atualizar_estatisticas_jogo(jogos_stats, jogo, dezenas, mes_sorteado):
    jogo_key = tuple(sorted(jogo['numeros']))
    acertos = len(set(jogo['numeros']) & set(dezenas))
    acertou_mes = jogo.get('mes') and jogo['mes'].upper() == mes_sorteado
    
    if jogo_key not in jogos_stats:
        jogos_stats[jogo_key] = {
            'numeros': list(jogo_key),
            'total': 0,
            'distribuicao': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0},
            'acertos_mes': 0
        }
    
    jogos_stats[jogo_key]['total'] += 1
    jogos_stats[jogo_key]['distribuicao'][acertos] += 1
    if acertou_mes:
        jogos_stats[jogo_key]['acertos_mes'] += 1

    return jogos_stats

@app.route('/exportar/<tipo>/<formato>', methods=['POST'])
def exportar_dados(tipo, formato):
    data = request.get_json()
    
    if tipo == 'resumo-acertos':
        df = pd.DataFrame({
            'Quantidade de Acertos': ['4 acertos', '5 acertos', '6 acertos', '7 acertos', 'Mês da Sorte'],
            'Total': [
                data['resumo']['quatro'],
                data['resumo']['cinco'],
                data['resumo']['seis'],
                data['resumo']['sete'],
                data['resumo']['mes']
            ],
            'Prêmio Total': [
                sum(r['premio'] for r in data['acertos'] if r['acertos'] == 4),
                sum(r['premio'] for r in data['acertos'] if r['acertos'] == 5),
                sum(r['premio'] for r in data['acertos'] if r['acertos'] == 6),
                sum(r['premio'] for r in data['acertos'] if r['acertos'] == 7),
                sum(r['premio'] for r in data['acertos'] if r['acertou_mes'])
            ]
        })
    
    elif tipo == 'jogos-premiados':
        df = pd.DataFrame([{
            'Concurso': r['concurso'],
            'Data': r['data'],
            'Números Sorteados': ' '.join(str(n) for n in r['numeros_sorteados']),
            'Mês Sorteado': r['mes_sorteado'],
            'Seus Números': ' '.join(str(n) for n in r['seus_numeros']),
            'Seu Mês': r['seu_mes'] or '',
            'Acertos': r['acertos'],
            'Acertou Mês': 'Sim' if r['acertou_mes'] else 'Não',
            'Prêmio': r['premio']
        } for r in data['acertos']])
    
    elif tipo == 'jogos-sorteados':
        if 'jogos_stats' in data:
            df = pd.DataFrame([{
                'Números': ' '.join(str(n) for n in jogo['numeros']),
                'Total de Acertos': jogo['total'],
                'Distribuição': ', '.join(f"{p} pontos: {v}x" for p, v in jogo['distribuicao'].items() if v > 0),
                'Acertos do Mês': jogo.get('acertos_mes', 0)
            } for jogo in data['jogos_stats']])
        else:
            return jsonify({'error': 'Dados de estatísticas não disponíveis'}), 400
    else:
        return jsonify({'error': 'Tipo de exportação inválido'}), 400

    if formato == 'xlsx':
        output = io.BytesIO()
        df.to_excel(output, index=False)
        output.seek(0)
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f"{tipo}.xlsx"
        )
    elif formato == 'html':
        return df.to_html(classes='table table-striped', index=False)
    else:
        return jsonify({'error': 'Formato de exportação inválido'}), 400

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)