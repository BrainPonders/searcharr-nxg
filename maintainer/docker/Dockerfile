# owner: project maintainer
# date: 2026-03-23
# service: Searcharr-nxg application container
# purpose: bootstrap image for the Searcharr-nxg service scaffold
# docs: maintainer/README.md, maintainer/development/README.md
# deployment notes:
#   - This image currently packages the scaffold runtime, not the finished Telegram bot.
#   - A local settings.py is expected at /app/settings.py when running the container.
# history:
#   - 2026-03-10: Initialized generic template image.
#   - 2026-03-23: Adapted the image for the Searcharr-nxg Python service scaffold.

FROM python:3.11-slim

ARG BUILD_NUMBER=local
ARG VERSION=dev-local

LABEL org.opencontainers.image.title="Searcharr-nxg"
LABEL org.opencontainers.image.description="Ryot-centric Telegram request system scaffold"
LABEL org.opencontainers.image.version="${VERSION}"

ENV APP_HOME=/app
ENV PROJECT_BUILD_NUMBER="${BUILD_NUMBER}"
ENV PROJECT_VERSION="${VERSION}"
ENV SEARCHARR_SETTINGS_FILE=/app/settings.py

WORKDIR /app

COPY pyproject.toml README.md requirements.txt ./
COPY src ./src
COPY lang ./lang

RUN set -eux; \
    python -m pip install --upgrade pip; \
    python -m pip install --no-cache-dir .

RUN mkdir -p /app/data
COPY maintainer/docker/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
