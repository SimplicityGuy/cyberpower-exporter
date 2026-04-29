# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3

FROM python:${PYTHON_VERSION}-slim-trixie

# Build arguments for labels
ARG BUILD_DATE
ARG BUILD_VERSION
ARG VCS_REF
ARG PYTHON_VERSION

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
      org.opencontainers.image.base.name="docker.io/library/python:${PYTHON_VERSION}-slim-trixie"

# hadolint ignore=DL3008
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

ARG PROMETHEUS_CLIENT_VERSION=0.21.1
RUN pip install --no-cache-dir \
        "prometheus_client==${PROMETHEUS_CLIENT_VERSION}" && \
    useradd -m -s /bin/bash -G root exporter && \
    mkdir /app && \
    chown exporter:exporter /app

COPY --chown=exporter:exporter exporter.py /app/exporter.py

USER exporter
WORKDIR /app

ENV LISTEN_ADDRESS=0.0.0.0:9200
EXPOSE 9200

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://127.0.0.1:9200/metrics > /dev/null || exit 1

CMD ["python", "/app/exporter.py"]
