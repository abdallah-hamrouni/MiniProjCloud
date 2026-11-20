FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN groupadd --system api && useradd --system --gid api --home-dir /app api \
    && chown api:api /app

COPY --chown=api:api main.py database.py models.py schemas.py security.py ./

USER api

EXPOSE 8000

CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port \"${PORT:-8000}\" --no-server-header"]
