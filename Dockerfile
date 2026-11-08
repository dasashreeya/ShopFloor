FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 SHOPFLOOR_DB_PATH=/app/data/shopfloor.db
COPY pyproject.toml README.md ./
COPY shopfloor ./shopfloor
RUN pip install --no-cache-dir .
COPY web ./web
# The package is installed into site-packages; serve web/ from the repo copy next to it.
ENV SHOPFLOOR_WEB_DIR=/app/web
EXPOSE 8000
CMD ["sh", "-c", "uvicorn shopfloor.api.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
