import redis
import os
from typing import Optional
import logging
import json
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
            
            if not redis_url:
                # Se não encontrar a URL, monta a partir das credenciais individuais
                redis_url = f"redis://:{os.getenv('REDIS_PASSWORD')}@{os.getenv('REDIS_HOST')}:{os.getenv('REDIS_PORT')}"
            
            self.logger.info(f"Tentando conectar ao Redis em: {redis_url.replace(os.getenv('REDIS_PASSWORD', ''), '****')}")
            
            client = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_timeout=5,
                retry_on_timeout=True
            )
            
            # Testa a conexão
            client.ping()
            self.logger.info("Conexão com Redis estabelecida com sucesso!")
            return client
            
        except Exception as e:
            self.logger.error(f"Erro ao conectar com Redis: {str(e)}")
            return None

    def get_cached_result(self, concurso: int) -> Optional[dict]:
        if not self.redis_client:
            return None
        try:
            cached = self.redis_client.get(f"diadesorte:{concurso}")
            if cached:
                return json.loads(cached)
            return None
        except Exception as e:
            self.logger.error(f"Erro ao recuperar cache do concurso {concurso}: {str(e)}")
            return None

    def set_cached_result(self, concurso: int, data: dict) -> bool:
        if not self.redis_client:
            return False
        try:
            self.redis_client.setex(
                f"diadesorte:{concurso}",
                self.CACHE_EXPIRATION,
                json.dumps(data, ensure_ascii=False)
            )
            return True
        except Exception as e:
            self.logger.error(f"Erro ao armazenar cache do concurso {concurso}: {str(e)}")
            return False

redis_config = RedisConfig()