"""
Envia todos os .txt da pasta documentos/ para a ingestao.

Rodar (local):   python -m servicos.ingestao.carregar
Rodar (Docker):  docker compose exec ingestao python -m servicos.ingestao.carregar
"""
import os
import pathlib

import requests

URL_INGESTAO = os.getenv("URL_INGESTAO", "http://localhost:8001")
PASTA = pathlib.Path(os.getenv("PASTA_DOCUMENTOS", "documentos"))

docs = [{"texto": p.read_text(encoding="utf-8").strip(), "origem": p.name}
        for p in sorted(PASTA.glob("*.txt"))]
r = requests.post(f"{URL_INGESTAO}/indexar", json=docs, timeout=10)
print(r.status_code, r.json())
