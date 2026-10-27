"""
Indice vetorial em disco, compartilhado pela API de ingestao e pelo worker.

- O WORKER e o unico que escreve (adicionar / limpar).
- A API apenas le (carregar) para responder /indice e /saude.
O arquivo fica em ARQUIVO_INDICE; no Docker, num volume que os dois enxergam.
"""
import json
import os

from servicos.comum.embeddings import Vetorizador

ARQUIVO_INDICE = os.getenv("ARQUIVO_INDICE", "indice.json")


def carregar():
    """Le o indice salvo em disco (ou devolve lista vazia se ainda nao existe)."""
    if not os.path.exists(ARQUIVO_INDICE):
        return []
    with open(ARQUIVO_INDICE, "r", encoding="utf-8") as f:
        return json.load(f)


def _salvar(itens):
    """Grava em arquivo temporario e renomeia: nunca deixa um JSON pela metade."""
    pasta = os.path.dirname(ARQUIVO_INDICE)
    if pasta:
        os.makedirs(pasta, exist_ok=True)
    temporario = ARQUIVO_INDICE + ".tmp"
    with open(temporario, "w", encoding="utf-8") as f:
        json.dump(itens, f, ensure_ascii=False)
    os.replace(temporario, ARQUIVO_INDICE)


def _mesmo_documento(a, b):
    """Mesmo documento = mesma origem (nome do arquivo); sem origem, mesmo texto."""
    if a["origem"] != "desconhecida":
        return a["origem"] == b["origem"]
    return a["texto"] == b["texto"]


def adicionar(docs):
    """Acrescenta documentos e recalcula TODOS os vetores com o mesmo vocabulario.

    Reenviar um documento que ja esta no indice SUBSTITUI a versao anterior em vez
    de duplicar: processar a mesma mensagem duas vezes da o mesmo resultado
    (idempotente), entao rodar o carregar de novo ou repetir uma mensagem e seguro.

    docs: lista de dicionarios com "texto" e "origem".
    Devolve o total de documentos no indice.
    """
    itens = carregar()
    for d in docs:
        texto = d["texto"].strip()
        if not texto:
            raise ValueError("documento com texto vazio")
        novo = {"texto": texto, "origem": d.get("origem") or "desconhecida"}
        itens = [i for i in itens if not _mesmo_documento(i, novo)]
        itens.append(novo)

    vetorizador = Vetorizador()
    vetorizador.ajustar([i["texto"] for i in itens])
    for i in itens:
        i["vetor"] = vetorizador.vetorizar(i["texto"])

    _salvar(itens)
    return len(itens)


def limpar():
    """Apaga o indice (util para repetir os testes do zero)."""
    if os.path.exists(ARQUIVO_INDICE):
        os.remove(ARQUIVO_INDICE)
