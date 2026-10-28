"""
Servico 2 - RECUPERACAO: dada uma pergunta, acha os trechos mais relevantes.

TAREFA 2: busca por similaridade (vetoriza a pergunta, compara com cada
documento do indice e devolve os top_k mais parecidos).

Rodar: uvicorn servicos.recuperacao.app:app --port 8002
"""
import os

import requests
from fastapi import FastAPI
from pydantic import BaseModel

from servicos.comum.embeddings import Vetorizador, similaridade

app = FastAPI(title="Recuperacao - C2.A2")
URL_INGESTAO = os.getenv("URL_INGESTAO", "http://localhost:8001")


class Consulta(BaseModel):
    pergunta: str
    top_k: int = 3


@app.post("/buscar")
def buscar(consulta: Consulta):
    """Devolve os top_k trechos mais parecidos com a pergunta."""
    r = requests.get(f"{URL_INGESTAO}/indice", timeout=10)
    r.raise_for_status()
    itens = r.json()["itens"]

    # indice vazio: nada a comparar, devolve lista vazia em vez de quebrar
    if not itens:
        return {"resultados": []}

    # Ajusta o vocabulario com os MESMOS textos que a ingestao usou.
    # Assim o vetor da pergunta fica no mesmo "espaco" dos vetores do indice.
    vetorizador = Vetorizador()
    vetorizador.ajustar([i["texto"] for i in itens])
    vetor_pergunta = vetorizador.vetorizar(consulta.pergunta)

    pontuados = [
        {"texto": i["texto"], "origem": i["origem"],
         "pontuacao": round(similaridade(vetor_pergunta, i["vetor"]), 4)}
        for i in itens
    ]
    pontuados.sort(key=lambda t: t["pontuacao"], reverse=True)

    top_k = max(consulta.top_k, 1)
    return {"resultados": pontuados[:top_k]}


@app.get("/saude")
def saude():
    return {"status": "ok"}
