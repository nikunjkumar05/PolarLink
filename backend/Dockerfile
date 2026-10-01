# PolarLink API — single-node image.
# SQLite + local file storage + ONNX embeddings, so one uvicorn worker only.
FROM python:3.12-slim AS build

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build
COPY backend/requirements.txt ./
RUN python -m pip install --prefix=/install -r requirements.txt


FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/install/bin:$PATH" \
    PYTHONPATH="/srv/polarlink/backend" \
    POLARLINK_DATA_DIR=/var/lib/polarlink/data \
    POLARLINK_STORAGE_DIR=/var/lib/polarlink/storage \
    FASTEMBED_CACHE_PATH=/var/cache/fastembed

# scripts/demo.py resolves the repo root as parents[2], so the app has to sit at
# <root>/backend for its sample-PDF output to land where the walkthrough expects.
COPY backend/app /srv/polarlink/backend/app
COPY backend/scripts /srv/polarlink/backend/scripts

RUN useradd --system --uid 10001 --home /srv/polarlink polarlink \
    && mkdir -p /srv/polarlink/demo \
        /var/lib/polarlink/data \
        /var/lib/polarlink/storage \
        /var/cache/fastembed \
    && chown -R polarlink:polarlink /srv/polarlink /var/lib/polarlink /var/cache/fastembed

COPY --from=build /install /usr/local

# Bake the embedding model into the image so the first search does not need the
# network, and the container still works behind a firewall.
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('BAAI/bge-small-en-v1.5').embed(['warm up'])" \
    && chown -R polarlink:polarlink /var/cache/fastembed

USER polarlink
WORKDIR /srv/polarlink/backend

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4).status==200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
