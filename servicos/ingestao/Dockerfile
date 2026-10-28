# Servico de ingestao (porta 8001). Build a partir da raiz do projeto (ver docker-compose.yml).
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY servicos/ servicos/
# documentos de teste, usados por: python -m servicos.ingestao.carregar
COPY documentos/ documentos/

EXPOSE 8001
CMD ["uvicorn", "servicos.ingestao.app:app", "--host", "0.0.0.0", "--port", "8001"]
