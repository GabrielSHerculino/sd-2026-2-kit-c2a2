"""
Servico 1 - INGESTAO: recebe documentos e os coloca na fila para indexacao.

TAREFA 1: indice persistido em disco e acumulativo (ver indice.py).
TAREFA 4: mensageria. POST /indexar so ENFILEIRA (resposta 202 imediata);
          quem gera os embeddings e grava o indice e o worker (worker.py).

Rodar: uvicorn servicos.ingestao.app:app --port 8001
       python -m servicos.ingestao.worker      (em outro terminal)
"""
import json

import redis
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from servicos.ingestao import fila, indice

app = FastAPI(title="Ingestao - C2.A2")


class Documento(BaseModel):
    texto: str
    origem: str = "desconhecida"


@app.post("/indexar", status_code=202)
def indexar(docs: list[Documento]):
    """Produtor: coloca cada documento na fila e responde na hora."""
    try:
        conexao = fila.conectar()
        if docs:
            conexao.rpush(fila.FILA, *[json.dumps({"texto": d.texto, "origem": d.origem,
                                                   "tentativas": 0}) for d in docs])
        na_fila = conexao.llen(fila.FILA)
    except redis.RedisError:
        raise HTTPException(503, "Fila (Redis) indisponivel: documento nao foi aceito. "
                                 "Tente novamente em alguns segundos.")
    return {"enfileirados": len(docs), "na_fila": na_fila}


@app.get("/indice")
def ver_indice():
    """Consumido pelo servico de recuperacao. Le do disco o que o worker gravou."""
    itens = indice.carregar()
    return {"total": len(itens),
            "itens": [{"texto": i["texto"], "origem": i["origem"],
                       "vetor": i["vetor"]} for i in itens]}


@app.delete("/indice")
def limpar_indice():
    """Zera o indice (util para repetir os testes do zero)."""
    indice.limpar()
    return {"total": 0}


@app.get("/saude")
def saude():
    estado = {"status": "ok", "documentos": len(indice.carregar())}
    try:
        conexao = fila.conectar()
        estado.update(fila_redis="ok", na_fila=conexao.llen(fila.FILA),
                      dead_letter=conexao.llen(fila.FILA_MORTA))
    except redis.RedisError:
        estado["fila_redis"] = "indisponivel"
    return estado
