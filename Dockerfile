FROM python:3.12.12-slim-bookworm AS dependencies

WORKDIR /build
COPY requirements-prod.txt .
RUN python -m pip wheel --no-cache-dir --wheel-dir=/wheels -r requirements-prod.txt

FROM python:3.12.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MODEL_PATH=/app/outputs/artifacts/model.joblib \
    PORT=8000

RUN apt-get update \
    && apt-get install --no-install-recommends -y libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system app \
    && useradd --system --gid app --home-dir /app --create-home app

WORKDIR /app
COPY --from=dependencies /wheels /wheels
COPY requirements-prod.txt .
RUN python -m pip install --no-cache-dir --no-index --find-links=/wheels \
        -r requirements-prod.txt \
    && rm -rf /wheels

COPY --chown=app:app app ./app
COPY --chown=app:app outputs/artifacts/model.joblib ./outputs/artifacts/model.joblib

USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
