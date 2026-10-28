"""
Servico 3 - GERACAO: monta o prompt com o contexto e chama o LLM.

TAREFA 3: resiliencia nas chamadas remotas.
  - LLM: tempo-limite (LLM_TIMEOUT, em llm.py) + retentativa com espera
    crescente + circuit breaker. Se falhar, responde 503 com mensagem clara
    e devolve os trechos recuperados (degrada com elegancia, nao quebra).
  - Recuperacao: circuit breaker proprio, para o servico de geracao nao ficar
    martelando a recuperacao quando ela esta fora do ar.

Rodar: uvicorn servicos.geracao.app:app --port 8003
"""
import logging
import os
import time

import requests
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from servicos.comum.circuit_breaker import CircuitBreaker, CircuitoAberto
from servicos.comum.llm import gerar

logging.basicConfig(level=logging.INFO, format="%(levelname)s [geracao] %(message)s")
log = logging.getLogger("geracao")

app = FastAPI(title="Geracao - C2.A2")
URL_RECUPERACAO = os.getenv("URL_RECUPERACAO", "http://localhost:8002")

TENTATIVAS_LLM = int(os.getenv("LLM_TENTATIVAS", "3"))
ESPERA_BASE = float(os.getenv("LLM_ESPERA_BASE", "1"))   # segundos: 1, 2, 4...

# um disjuntor para cada dependencia remota
disjuntor = CircuitBreaker(limite_falhas=3, espera_segundos=20)               # LLM
disjuntor_recuperacao = CircuitBreaker(limite_falhas=3, espera_segundos=20)   # recuperacao


class Pergunta(BaseModel):
    pergunta: str


def _buscar_contexto(pergunta):
    """Chama a recuperacao e devolve a lista de trechos."""
    r = requests.post(f"{URL_RECUPERACAO}/buscar",
                      json={"pergunta": pergunta, "top_k": 3}, timeout=10)
    r.raise_for_status()
    return [t["texto"] for t in r.json()["resultados"]]


def _gerar_com_retentativa(pergunta, contexto):
    """Chama o LLM ate TENTATIVAS_LLM vezes, esperando mais a cada falha.

    Gerar uma resposta e idempotente (nao altera nada), entao repetir e seguro.
    So depois de esgotar as tentativas a excecao sobe e o disjuntor conta
    UMA falha.
    """
    for tentativa in range(1, TENTATIVAS_LLM + 1):
        try:
            return gerar(pergunta, contexto)
        except requests.RequestException as erro:   # timeout, conexao, HTTP 4xx/5xx
            if tentativa == TENTATIVAS_LLM:
                log.warning("LLM falhou na tentativa %d/%d (%s): desistindo",
                            tentativa, TENTATIVAS_LLM, type(erro).__name__)
                raise
            espera = ESPERA_BASE * 2 ** (tentativa - 1)
            log.warning("LLM falhou na tentativa %d/%d (%s): nova tentativa em %.1fs",
                        tentativa, TENTATIVAS_LLM, type(erro).__name__, espera)
            time.sleep(espera)


def _indisponivel(mensagem, pergunta, contexto=None):
    return JSONResponse(status_code=503, content={
        "erro": mensagem, "pergunta": pergunta, "contexto": contexto or []})


@app.post("/perguntar")
def perguntar(p: Pergunta):
    # 1) recuperacao, protegida pelo seu disjuntor
    try:
        contexto = disjuntor_recuperacao.chamar(_buscar_contexto, p.pergunta)
    except CircuitoAberto:
        return _indisponivel("Servico de recuperacao indisponivel (circuito aberto). "
                             "Tente novamente em alguns segundos.", p.pergunta)
    except requests.RequestException as erro:
        log.warning("recuperacao falhou: %s", type(erro).__name__)
        return _indisponivel("Servico de recuperacao indisponivel no momento.", p.pergunta)
    except (KeyError, TypeError, ValueError) as erro:   # resposta fora do contrato
        log.warning("recuperacao devolveu resposta invalida: %s", type(erro).__name__)
        return _indisponivel("Servico de recuperacao devolveu uma resposta invalida.", p.pergunta)

    # 2) LLM: timeout (llm.py) + retentativa + disjuntor
    try:
        resposta = disjuntor.chamar(_gerar_com_retentativa, p.pergunta, contexto)
    except CircuitoAberto:
        return _indisponivel("LLM indisponivel (circuito aberto). Seguem os trechos "
                             "recuperados; tente novamente em alguns segundos.",
                             p.pergunta, contexto)
    except requests.RequestException:
        return _indisponivel(f"LLM nao respondeu apos {TENTATIVAS_LLM} tentativas. "
                             "Seguem os trechos recuperados.", p.pergunta, contexto)
    except Exception as erro:   # resposta fora do formato esperado (ex.: JSON sem "choices")
        log.warning("LLM devolveu resposta invalida: %s", type(erro).__name__)
        return _indisponivel("LLM devolveu uma resposta invalida. Seguem os trechos "
                             "recuperados.", p.pergunta, contexto)

    return {"pergunta": p.pergunta, "resposta": resposta, "contexto": contexto}


@app.get("/saude")
def saude():
    return {"status": "ok",
            "disjuntor_llm": disjuntor.estado,
            "disjuntor_recuperacao": disjuntor_recuperacao.estado}
