# syntax=docker/dockerfile:1.7

# ---------- builder: instala dependências em um venv isolado ----------
FROM python:3.12-slim-bookworm AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# camada de dependências separada do código: rebuild só quando o pyproject muda.
# instala com um pacote stub para resolver as dependências sem copiar o código,
# e remove o stub em seguida — as dependências permanecem no venv.
COPY apps/api/pyproject.toml ./pyproject.toml
RUN pip install --upgrade pip setuptools wheel \
 && mkdir -p app && touch app/__init__.py \
 && pip install . \
 && pip uninstall --yes rfbalance-api

# ---------- runtime: imagem final, sem ferramenta de build, sem root ----------
FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

# Cliente usado pelo job de backup lógico. A senha é fornecida por ambiente,
# nunca como argumento visível na lista de processos.
RUN apt-get update \
 && apt-get install --yes --no-install-recommends default-mysql-client \
 && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid 1000 app \
 && useradd --uid 1000 --gid app --create-home app

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
RUN chown app:app /app
COPY --chown=app:app apps/api/alembic.ini ./alembic.ini
COPY --chown=app:app apps/api/pyproject.toml ./pyproject.toml
COPY --chown=app:app apps/api/migrations ./migrations
COPY --chown=app:app apps/api/app ./app
COPY --chown=app:app apps/worker ./worker

USER app
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ---------- dev: recarga automática, dependências de teste ----------
FROM runtime AS dev

# caches fora de /app: o diretório é bind mount em dev e não deve receber lixo
ENV RUFF_CACHE_DIR=/tmp/.ruff_cache \
    MYPY_CACHE_DIR=/tmp/.mypy_cache \
    PYTEST_ADDOPTS="-p no:cacheprovider"

USER root
# instala o extra [dev] do próprio pyproject: as versões de teste ficam em um
# único lugar, sem duplicar pins aqui
COPY apps/api/pyproject.toml /tmp/dev/pyproject.toml
RUN cd /tmp/dev \
 && mkdir -p app && touch app/__init__.py \
 && pip install --no-cache-dir ".[dev]" \
 && pip uninstall --yes rfbalance-api \
 && rm -rf /tmp/dev
USER app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
