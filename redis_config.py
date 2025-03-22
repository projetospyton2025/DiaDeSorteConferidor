import redis
import os
from typing import Optional
import logging
import json
from ast import literal_eval
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()

class RedisConfig:
    def __init__(self):
        self.logger = self._setup_logger()
        self.redis_client = self._initialize_redis()
        self.CACHE_EXPIRATION = 60 * 60 * 24  # 24 horas

    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger('RedisConfig')
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

    def _initialize_redis(self) -> Optional[redis.Redis]:
        try:
            # Tenta primeiro usar a URL completa do Redis
            redis_url = os.getenv("REDIS_URL")
            
            if redis_url:
                # Verifica se a URL tem formato correto
                self.logger.info(f"Tentando conectar ao Redis com URL: {redis_url.replace(os.getenv('REDIS_PASSWORD', ''), '****')}")
                
                # Se a URL contém credenciais diretas, formato correto para o redis.from_url
                try:
                    client = redis.from_url(
                        redis_url,
                        decode_responses=True,
                        socket_timeout=10,
                        socket_connect_timeout=10,
                        retry_on_timeout=True
                    )
                    # Testa a conexão
                    client.ping()
                    self.logger.info("Conexão com Redis estabelecida com sucesso via URL!")
                    return client
                except Exception as e:
                    self.logger.error(f"Erro ao conectar com Redis via URL: {str(e)}")
                    # Falha na URL, vamos tentar com os parâmetros individuais
            
            # Tenta conectar usando parâmetros individuais
            self.logger.info(f"Tentando conectar ao Redis com parâmetros individuais: {os.getenv('REDIS_HOST')}:{os.getenv('REDIS_PORT')}")
            
            client = redis.Redis(
                host=os.getenv('REDIS_HOST'),
                port=int(os.getenv('REDIS_PORT', 6379)),
                password=os.getenv('REDIS_PASSWORD'),
                db=int(os.getenv('REDIS_DB', 0)),
                decode_responses=True,
                socket_timeout=10,
                socket_connect_timeout=10,
                retry_on_timeout=True
            )
            
            # Testa a conexão
            client.ping()
            self.logger.info("Conexão com Redis estabelecida com sucesso via parâmetros individuais!")
            return client
            
        except Exception as e:
            self.logger.error(f"Erro ao conectar com Redis: {str(e)}")
            self.logger.info("O sistema continuará funcionando sem cache Redis.")
            return None

    def get_cached_result(self, concurso: int) -> Optional[dict]:
        if not self.redis_client:
            return None
        try:
            cached = self.redis_client.get(f"diadesorte:{concurso}")
            if cached:
                try:
                    return json.loads(cached)
                except json.JSONDecodeError:
                    try:
                        return literal_eval(cached)
                    except (ValueError, SyntaxError):
                        self.logger.error(f"Erro ao desserializar cache para concurso {concurso}")
                        return None
            return None
        except Exception as e:
            self.logger.error(f"Erro ao recuperar cache do concurso {concurso}: {str(e)}")
            return None

    def set_cached_result(self, concurso: int, data: dict) -> bool:
        if not self.redis_client:
            return False
        try:
            serialized = json.dumps(data, ensure_ascii=False)
            self.redis_client.setex(
                f"diadesorte:{concurso}",
                self.CACHE_EXPIRATION,
                serialized
            )
            return True
        except Exception as e:
            self.logger.error(f"Erro ao armazenar cache do concurso {concurso}: {str(e)}")
            return False

redis_config = RedisConfig()