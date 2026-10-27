"""
Fila de ingestao no Redis (TAREFA 4).

Produtor (API):  RPUSH fila_ingestao <documento em JSON>
Consumidor (worker): BLPOP fila_ingestao
Mensagens que falham MAX_TENTATIVAS vezes vao para fila_ingestao_dead (dead-letter).
"""
import os

import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
FILA = "fila_ingestao"
FILA_MORTA = "fila_ingestao_dead"
MAX_TENTATIVAS = int(os.getenv("INGESTAO_TENTATIVAS", "3"))


def conectar(socket_timeout=2):
    return redis.Redis.from_url(REDIS_URL, decode_responses=True,
                                socket_connect_timeout=2,
                                socket_timeout=socket_timeout)
