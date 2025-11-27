FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY services/codereview/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY services/codereview/ .

RUN addgroup --gid 1000 appuser && \
    adduser --uid 1000 --gid 1000 --disabled-password --gecos "" appuser && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["python", "main.py"]
