FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./

RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY api ./api
COPY pipeline_runtime.py ./

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=5 \
  CMD curl -fsS "http://localhost:${PORT}/health" > /dev/null || exit 1

CMD ["sh", "-c", "gunicorn -k uvicorn.workers.UvicornWorker api.main:app --bind 0.0.0.0:${PORT} --timeout 180 --access-logfile - --error-logfile -"]
