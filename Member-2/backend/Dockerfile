FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    APP_ENV=production \
    STORAGE_DIR=/data/storage \
    WEB_CONCURRENCY=2

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

RUN useradd --create-home --uid 10001 app \
    && mkdir -p /data/storage && chown app:app /data/storage

COPY alembic.ini ./
COPY migrations ./migrations
COPY rules ./rules
COPY fonts ./fonts
COPY app ./app

USER app
EXPOSE 8000
VOLUME ["/data/storage"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)"

# Migrate, then serve. FORWARDED_ALLOW_IPS = your reverse proxy's IP, so rate limits see
# the real client IP from X-Forwarded-For.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers ${WEB_CONCURRENCY} --proxy-headers --forwarded-allow-ips ${FORWARDED_ALLOW_IPS:-127.0.0.1} --no-server-header"]
