# Servico de recuperacao (porta 8002). Build a partir da raiz do projeto (ver docker-compose.yml).
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY servicos/ servicos/

EXPOSE 8002
CMD ["uvicorn", "servicos.recuperacao.app:app", "--host", "0.0.0.0", "--port", "8002"]
