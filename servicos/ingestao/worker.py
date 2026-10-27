"""
Worker de ingestao (TAREFA 4): consome a fila e indexa os documentos.

Rodar: python -m servicos.ingestao.worker

- Pega um documento por vez da fila (BLPOP), adiciona ao indice e grava em disco.
- Se a indexacao falhar, devolve a mensagem para o fim da fila com o contador
  de tentativas; apos MAX_TENTATIVAS, manda para a dead-letter.
- Se o Redis cair, espera e tenta reconectar (nao derruba o processo).
"""
import json
import logging
import time

import redis

from servicos.ingestao import fila, indice

logging.basicConfig(level=logging.INFO, format="%(levelname)s [worker] %(message)s")
log = logging.getLogger("worker")


def processar(conexao, mensagem):
    doc = json.loads(mensagem)
    try:
        total = indice.adicionar([doc])
        log.info("indexado '%s' (indice com %d documentos)", doc.get("origem"), total)
    except Exception as erro:
        doc["tentativas"] = doc.get("tentativas", 0) + 1
        if doc["tentativas"] >= fila.MAX_TENTATIVAS:
            conexao.rpush(fila.FILA_MORTA, json.dumps(doc))
            log.error("'%s' falhou %d vezes (%s): enviado para a dead-letter",
                      doc.get("origem"), doc["tentativas"], erro)
        else:
            conexao.rpush(fila.FILA, json.dumps(doc))
            log.warning("'%s' falhou (%s): tentativa %d/%d, devolvido para a fila",
                        doc.get("origem"), erro, doc["tentativas"], fila.MAX_TENTATIVAS)


def main():
    log.info("aguardando documentos na fila '%s' (%s)", fila.FILA, fila.REDIS_URL)
    conexao = fila.conectar(socket_timeout=10)
    while True:
        try:
            item = conexao.blpop(fila.FILA, timeout=5)   # espera ate 5 s por uma mensagem
            if item:
                processar(conexao, item[1])
        except redis.RedisError as erro:
            log.warning("Redis indisponivel (%s): nova tentativa em 3 s", type(erro).__name__)
            time.sleep(3)


if __name__ == "__main__":
    main()
