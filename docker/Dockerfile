# SynaptiQ ResearchOS — FastAPI backend image
# Build: docker build -f docker/Dockerfile -t synaptiq-api ../backend

FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip wheel --wheel-dir /wheels -r requirements.txt


FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 1001 synaptiq \
    && useradd --system --uid 1001 --gid synaptiq --create-home synaptiq

COPY --from=builder /wheels /wheels
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels

COPY --chown=synaptiq:synaptiq . .

RUN sed -i 's/\r$//' /app/entrypoint.sh \
    && chmod +x /app/entrypoint.sh

USER synaptiq

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/health || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
