#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
REPO_PARENT_DIR="$(cd "$REPO_DIR/.." && pwd)"

slugify() {
    printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | tr -cs '[:alnum:]' '-'
}

PROJECT_SLUG="${PROJECT_SLUG:-$(slugify "$(basename "$REPO_DIR")")}"
PROJECT_IMAGE_NAME="${PROJECT_IMAGE_NAME:-$PROJECT_SLUG}"
PROJECT_DEV_PROJECT="${PROJECT_DEV_PROJECT:-${PROJECT_SLUG}-dev}"
PROJECT_DEV_ROOT="${PROJECT_DEV_ROOT:-${REPO_PARENT_DIR}/${PROJECT_SLUG}-dev}"
PROJECT_DOCKERFILE_PATH="${PROJECT_DOCKERFILE_PATH:-$REPO_DIR/maintainer/docker/Dockerfile}"
PROJECT_SETTINGS_SAMPLE_PATH="${PROJECT_SETTINGS_SAMPLE_PATH:-$REPO_DIR/settings-sample.py}"
PROJECT_DEV_UP="${PROJECT_DEV_UP:-0}"

RUNTIME_COMPOSE="$PROJECT_DEV_ROOT/docker-compose.yml"
RUNTIME_ENV="$PROJECT_DEV_ROOT/.env"
RUNTIME_DATA_DIR="$PROJECT_DEV_ROOT/data"
RUNTIME_CONFIG_DIR="$PROJECT_DEV_ROOT/config"
RUNTIME_SETTINGS="$RUNTIME_CONFIG_DIR/settings.py"
TEMPLATE_COMPOSE="$REPO_DIR/docker/compose/docker-compose-dev.yml.example"
TEMPLATE_ENV="$REPO_DIR/docker/compose/.env.dev.example"

compose_run() {
    if docker compose version >/dev/null 2>&1; then
        docker compose "$@"
        return
    fi

    if command -v docker-compose >/dev/null 2>&1; then
        docker-compose "$@"
        return
    fi

    echo "ERROR: Docker Compose is not available."
    exit 1
}

if [ ! -f "$PROJECT_DOCKERFILE_PATH" ]; then
    echo "ERROR: Dockerfile not found at $PROJECT_DOCKERFILE_PATH"
    exit 1
fi

if [ ! -f "$TEMPLATE_COMPOSE" ]; then
    echo "ERROR: Missing dev compose template: $TEMPLATE_COMPOSE"
    exit 1
fi

if [ ! -f "$TEMPLATE_ENV" ]; then
    echo "ERROR: Missing dev env template: $TEMPLATE_ENV"
    exit 1
fi

if [ ! -f "$PROJECT_SETTINGS_SAMPLE_PATH" ]; then
    echo "ERROR: Missing settings sample: $PROJECT_SETTINGS_SAMPLE_PATH"
    exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
    echo "ERROR: docker is not installed."
    exit 1
fi

BUILD_NUMBER="$(git -C "$REPO_DIR" rev-list --count HEAD 2>/dev/null || printf '%s' "local")"
SHORT_SHA="$(git -C "$REPO_DIR" rev-parse --short=12 HEAD 2>/dev/null || printf '%s' "local")"
IMAGE_REF="${PROJECT_IMAGE_NAME}:dev-${SHORT_SHA}"

echo "== Build image ${IMAGE_REF} =="
docker build \
    --build-arg BUILD_NUMBER="${BUILD_NUMBER}" \
    --build-arg VERSION="dev-${SHORT_SHA}" \
    -t "${IMAGE_REF}" \
    -t "${PROJECT_IMAGE_NAME}:dev-latest" \
    -f "$PROJECT_DOCKERFILE_PATH" \
    "$REPO_DIR"

echo "== Prepare runtime folder: ${PROJECT_DEV_ROOT} =="
mkdir -p "$PROJECT_DEV_ROOT" "$RUNTIME_DATA_DIR" "$RUNTIME_CONFIG_DIR"

if [ ! -f "$RUNTIME_COMPOSE" ]; then
    cp "$TEMPLATE_COMPOSE" "$RUNTIME_COMPOSE"
    echo "Created ${RUNTIME_COMPOSE}"
elif ! cmp -s "$TEMPLATE_COMPOSE" "$RUNTIME_COMPOSE"; then
    cp "$TEMPLATE_COMPOSE" "${RUNTIME_COMPOSE}.new"
    echo "Template updated: ${RUNTIME_COMPOSE}.new (existing file preserved)"
fi

RUNTIME_ENV_CREATED=false
if [ ! -f "$RUNTIME_ENV" ]; then
    cp "$TEMPLATE_ENV" "$RUNTIME_ENV"
    RUNTIME_ENV_CREATED=true
    echo "Created ${RUNTIME_ENV}"
elif ! cmp -s "$TEMPLATE_ENV" "$RUNTIME_ENV"; then
    cp "$TEMPLATE_ENV" "${RUNTIME_ENV}.new"
    echo "Template updated: ${RUNTIME_ENV}.new (existing file preserved)"
fi

if [ ! -f "$RUNTIME_SETTINGS" ]; then
    cp "$PROJECT_SETTINGS_SAMPLE_PATH" "$RUNTIME_SETTINGS"
    echo "Created ${RUNTIME_SETTINGS}"
fi

if grep -q '^PROJECT_IMAGE=' "$RUNTIME_ENV"; then
    sed -i.bak "s|^PROJECT_IMAGE=.*$|PROJECT_IMAGE=${IMAGE_REF}|" "$RUNTIME_ENV"
    rm -f "${RUNTIME_ENV}.bak"
else
    printf '\nPROJECT_IMAGE=%s\n' "$IMAGE_REF" >> "$RUNTIME_ENV"
fi

if [ "$RUNTIME_ENV_CREATED" = true ] && ! grep -q '^PROJECT_SETTINGS_FILE=' "$RUNTIME_ENV"; then
    printf 'PROJECT_SETTINGS_FILE=./config/settings.py\n' >> "$RUNTIME_ENV"
fi

if [ "$PROJECT_DEV_UP" = "1" ]; then
    echo "== Start dev container =="
    (
        cd "$PROJECT_DEV_ROOT"
        compose_run \
            -p "$PROJECT_DEV_PROJECT" \
            --env-file "$RUNTIME_ENV" \
            -f "$RUNTIME_COMPOSE" \
            up -d --pull never --force-recreate
    )
else
    echo "== Runtime files prepared; container start skipped =="
fi

echo "== Done =="
echo "Image: ${IMAGE_REF}"
echo "Compose project: ${PROJECT_DEV_PROJECT}"
echo "Runtime folder: ${PROJECT_DEV_ROOT}"
echo "Settings file: ${RUNTIME_SETTINGS}"
echo "Review ${RUNTIME_ENV}, ${RUNTIME_COMPOSE}, and ${RUNTIME_SETTINGS} before starting the container."
