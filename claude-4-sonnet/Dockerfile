FROM python:3.11-slim

RUN groupadd -r botuser && useradd -r -g botuser botuser

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/logs && chown -R botuser:botuser /app

USER botuser

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import os; exit(0 if os.environ.get('TELEGRAM_BOT_TOKEN') else 1)"

CMD ["python", "-u", "main.py"]