# owner: project maintainer
# date: 2026-03-23
# service: Searcharr-nxg application container
# purpose: application image for the Searcharr-nxg runtime
# docs: maintainer/README.md, maintainer/development/README.md
# deployment notes:
#   - This image packages the current Telegram bot runtime and CLI helpers.
#   - A local settings.py is expected at /app/settings.py when running the container.
# history:
#   - 2026-03-10: Initialized generic template image.
#   - 2026-03-23: Adapted the image for the Searcharr-nxg Python service runtime.
#   - 2026-03-25: Rebased on 11notes/python for the public release path.

FROM 11notes/python:3.12

ARG BUILD_NUMBER=local
ARG VERSION=dev-local

LABEL org.opencontainers.image.title="Searcharr-nxg"
LABEL org.opencontainers.image.description="Ryot-centric Telegram request system for Radarr and Sonarr"
LABEL org.opencontainers.image.version="${VERSION}"
LABEL org.opencontainers.image.source="https://github.com/BrainPonders/searcharr-nxg"

ENV APP_HOME=/app
ENV PROJECT_BUILD_NUMBER="${BUILD_NUMBER}"
ENV PROJECT_VERSION="${VERSION}"
ENV SEARCHARR_SETTINGS_FILE=/app/settings.py
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

USER root

WORKDIR /app

COPY pyproject.toml README.md requirements.txt ./
COPY src ./src
COPY lang ./lang

RUN set -eux; \
    python -m pip install --no-cache-dir .

RUN mkdir -p /app/data && chown -R 1000:1000 /app
COPY maintainer/docker/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

USER 1000:1000

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
