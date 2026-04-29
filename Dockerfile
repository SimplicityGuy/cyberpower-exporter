# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.13
ARG UID=1000
ARG GID=1000

# nosemgrep: dockerfile.security.missing-user.missing-user
FROM python:${PYTHON_VERSION}-slim AS builder

# Install uv from the official image
COPY --from=ghcr.io/astral-sh/uv:0.11.8 /uv /bin/uv

ENV UV_SYSTEM_PYTHON=1 \
    UV_CACHE_DIR=/tmp/.cache/uv \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Copy dependency manifests first for better layer caching
COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/

# hadolint ignore=SC2015
RUN --mount=type=cache,target=/tmp/.cache/uv \
    uv sync --frozen --no-dev && \
    find /app/.venv -type f -name "*.pyc" -delete && \
    find /app/.venv -type f -name "*.pyo" -delete && \
    find /app/.venv -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true && \
    find /app/.venv -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true && \
    find /app/.venv -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true && \
    find /app/.venv -name "*.so" -exec strip --strip-unneeded {} \; 2>/dev/null || true

# Final stage
FROM python:${PYTHON_VERSION}-slim

ARG BUILD_DATE
ARG BUILD_VERSION
ARG VCS_REF
ARG PYTHON_VERSION
ARG UID=1000
ARG GID=1000

# OCI Image Spec Annotations
# https://github.com/opencontainers/image-spec/blob/main/annotations.md
LABEL org.opencontainers.image.title="cyberpower-exporter" \
      org.opencontainers.image.description="Prometheus exporter for CyberPower UPS systems. Reads pwrstatd over a Unix socket and exposes metrics on port 9200." \
      org.opencontainers.image.authors="Robert Wlodarczyk <robert@simplicityguy.com>" \
      org.opencontainers.image.url="https://github.com/SimplicityGuy/cyberpower-exporter" \
      org.opencontainers.image.documentation="https://github.com/SimplicityGuy/cyberpower-exporter/blob/main/README.md" \
      org.opencontainers.image.source="https://github.com/SimplicityGuy/cyberpower-exporter" \
      org.opencontainers.image.vendor="SimplicityGuy" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.version="${BUILD_VERSION:-0.1.0}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.base.name="docker.io/library/python:${PYTHON_VERSION}-slim"

# hadolint ignore=DL3008
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Create user and directories. Add to root group so the host pwrstatd socket is readable.
RUN groupadd -r -g ${GID} exporter && \
    useradd -r -l -u ${UID} -g exporter -G root -m -s /bin/bash exporter && \
    mkdir -p /app && \
    chown -R exporter:exporter /app

WORKDIR /app

COPY --from=builder --chown=exporter:exporter /app/.venv /app/.venv

ENV LISTEN_ADDRESS=0.0.0.0:9200 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

EXPOSE 9200

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://127.0.0.1:9200/metrics > /dev/null || exit 1

USER exporter:exporter

# Security: This container should be run with:
# docker run --cap-drop=ALL --security-opt=no-new-privileges:true ...

CMD ["cyberpower-exporter"]
