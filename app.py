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
# Altere a linha:
# API_BASE_URL = "https://loteriascaixa-api.herokuapp.com/api"  # API principal
API_BASE_URL = "https://servicebus2.caixa.gov.br/portaldeloterias/api"  # API alternativa (comentada)


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
                        # Divide a linha em números e possivelmente um mês
                        partes = line.strip().split()
                        
                        # Extrai os números (primeiros 7 valores)
                        numbers = []
                        mes = None
                        
                        for i, parte in enumerate(partes):
                            if i < 7:  # Primeiros 7 valores são números
                                try:
                                    num = int(parte)
                                    if 1 <= num <= 31:
                                        numbers.append(num)
                                except ValueError:
                                    continue
                            else:  # O que vier depois pode ser o mês
                                mes = normalizar_mes(parte)
                                break
                                
                        if len(numbers) == 7 and all(1 <= n <= 31 for n in numbers) and len(set(numbers)) == 7:
                            jogos.append({'numeros': sorted(numbers), 'mes': mes})
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
                                mes_valor = str(row.values[7])
                                mes = normalizar_mes(mes_valor)
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
        
        # Validação de entrada
        if not jogos or not isinstance(jogos, list):
            return jsonify({
                'error': 'Formato inválido: jogos deve ser uma lista não vazia',
                'detail': 'Verifique o formato dos jogos enviados'
            }), 400
            
        for jogo in jogos:
            if 'numeros' not in jogo or len(jogo['numeros']) != 7:
                return jsonify({
                    'error': 'Formato inválido: cada jogo deve ter 7 números',
                    'detail': 'Verifique se todos os jogos possuem 7 números'
                }), 400

        # Pega os números dos concursos
        inicio = int(data.get('inicio', 1))
        fim = int(data.get('fim', await obter_ultimo_concurso()))

        logger.info(f"\n{'='*50}")
        logger.info(f"Iniciando conferência com {len(jogos)} jogos")
        logger.info("Detalhes dos jogos a serem conferidos:")
        for idx, jogo in enumerate(jogos[:5], 1):  # Mostrar apenas os 5 primeiros para não sobrecarregar o log
            numeros_formatados = ', '.join(str(n).zfill(2) for n in sorted(jogo['numeros']))
            mes_info = f" | Mês: {jogo.get('mes', 'não informado')}" if jogo.get('mes') else ""
            logger.info(f"Jogo {idx}: [{numeros_formatados}]{mes_info}")
        if len(jogos) > 5:
            logger.info(f"... e mais {len(jogos) - 5} jogos")
        logger.info(f"{'='*50}\n")
        
        # Definição dos lotes de concursos
        logger.info(f"Faixa de concursos a verificar: {inicio} até {fim}")
        logger.info(f"Total de concursos a processar: {fim - inicio + 1}")
        
        # Usa o processador em lotes com tratamento de erros melhorado
        try:
            resultados = await processar_todos_jogos(inicio, fim, jogos)
            return jsonify(resultados)
        except Exception as e:
            logger.error(f"Erro no processador de lotes: {str(e)}")
            logger.exception("Stack trace completo:")
            return jsonify({
                'error': 'Erro ao processar jogos',
                'message': str(e),
                'detail': 'Erro durante o processamento dos lotes de concursos'
            }), 500

    except KeyError as e:
        logger.error(f"Erro de campo obrigatório: {str(e)}")
        return jsonify({
            'error': 'Campo obrigatório ausente',
            'message': f"Campo {str(e)} não encontrado no request",
            'detail': 'Verifique se todos os campos obrigatórios estão presentes'
        }), 400
    except ValueError as e:
        logger.error(f"Erro de valor: {str(e)}")
        return jsonify({
            'error': 'Valor inválido',
            'message': str(e),
            'detail': 'Verifique se os valores fornecidos estão no formato correto'
        }), 400
    except Exception as e:
        logger.error(f"Erro geral na conferência: {str(e)}")
        logger.exception("Stack trace completo:")
        return jsonify({
            'error': 'Erro ao processar jogos',
            'message': str(e),
            'detail': 'Ocorreu um erro inesperado durante o processamento'
        }), 500


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
                    if resultado:
                        # Verifica se a estrutura é da API principal ou alternativa
                        if 'dezenas' in resultado:
                            # Formato da API principal
                            resultado_normalizado = {
                                'concurso': resultado.get('concurso'),
                                'data': resultado.get('data'),
                                'dezenas': resultado.get('dezenas'),
                                'mesDaSorte': resultado.get('mesDaSorte', ''),
                                'premiacoes': resultado.get('premiacoes', [])
                            }
                        elif 'listaDezenas' in resultado:
                            # Formato da API alternativa
                            resultado_normalizado = {
                                'concurso': resultado.get('numero'),
                                'data': resultado.get('dataApuracao'),
                                'dezenas': resultado.get('listaDezenas'),
                                'mesDaSorte': resultado.get('nomeTimeCoracaoMesSorte', ''),
                                'premiacoes': []
                            }
                            
                            # Converter o formato de premiações
                            if 'listaRateioPremio' in resultado:
                                for premio in resultado['listaRateioPremio']:
                                    resultado_normalizado['premiacoes'].append({
                                        'descricao': premio.get('descricaoFaixa', ''),
                                        'ganhadores': premio.get('numeroDeGanhadores', 0),
                                        'valorPremio': premio.get('valorPremio', 0)
                                    })
                        else:
                            # Formato desconhecido
                            resultado_normalizado = resultado
                        
                        redis_config.set_cached_result(concurso, resultado_normalizado)
                        return resultado_normalizado
                
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


def normalizar_mes(mes_abreviado):
    """Converte mês abreviado para o formato completo"""
    meses_map = {
        "JAN": "JANEIRO",
        "FEV": "FEVEREIRO",
        "MAR": "MARÇO", 
        "ABR": "ABRIL",
        "MAI": "MAIO",
        "JUN": "JUNHO",
        "JUL": "JULHO",
        "AGO": "AGOSTO",
        "SET": "SETEMBRO",
        "OUT": "OUTUBRO",
        "NOV": "NOVEMBRO",
        "DEZ": "DEZEMBRO"
    }
    
    if not mes_abreviado:
        return None
        
    mes_upper = mes_abreviado.upper()
    
    # Se já for o nome completo
    if mes_upper in [m.upper() for m in MESES]:
        return mes_upper
        
    # Se for abreviado
    if mes_upper in meses_map:
        return meses_map[mes_upper]
        
    # Verifica se é uma abreviação de 3 letras para qualquer mês
    for abrev, completo in meses_map.items():
        if completo.upper().startswith(mes_upper):
            return completo
            
    return mes_upper  # Retorna o que foi fornecido se não encontrar correspondência

if __name__ == '__main__':
    #port = int(os.environ.get("PORT", 10000))
    port = int(os.environ.get("PORT", 500))
    app.run(host="0.0.0.0", port=port)