#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

slugify() {
    printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | tr -cs '[:alnum:]' '-'
}

PROJECT_IMAGE_NAME="${PROJECT_IMAGE_NAME:-$(slugify "$(basename "$REPO_DIR")")}"
PROJECT_IMAGE_TAG="${PROJECT_IMAGE_TAG:-}"
PROJECT_DOCKERFILE_PATH="${PROJECT_DOCKERFILE_PATH:-$REPO_DIR/maintainer/docker/Dockerfile}"

build_number_default() {
    if command -v git >/dev/null 2>&1 && git -C "$REPO_DIR" rev-parse --git-dir >/dev/null 2>&1; then
        git -C "$REPO_DIR" rev-list --count HEAD 2>/dev/null || printf '%s' "local"
    else
        printf '%s' "local"
    fi
}

short_sha_default() {
    if command -v git >/dev/null 2>&1 && git -C "$REPO_DIR" rev-parse --git-dir >/dev/null 2>&1; then
        git -C "$REPO_DIR" rev-parse --short=12 HEAD 2>/dev/null || printf '%s' "local"
    else
        printf '%s' "local"
    fi
}

if [ ! -f "$PROJECT_DOCKERFILE_PATH" ]; then
    echo "ERROR: Dockerfile not found at $PROJECT_DOCKERFILE_PATH"
    exit 1
fi

if [ -z "$PROJECT_IMAGE_TAG" ]; then
    echo "ERROR: PROJECT_IMAGE_TAG is required."
    echo "Example:"
    echo "  PROJECT_IMAGE_TAG=v0.1.0 bash maintainer/release/release.sh"
    exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
    echo "ERROR: docker is not installed."
    exit 1
fi

if ! docker info >/dev/null 2>&1; then
    echo "ERROR: docker daemon is not running."
    exit 1
fi

PROJECT_BUILD_NUMBER="${PROJECT_BUILD_NUMBER:-$(build_number_default)}"
PROJECT_VERSION="${PROJECT_VERSION:-${PROJECT_IMAGE_TAG}}"
PROJECT_GIT_SHA="${PROJECT_GIT_SHA:-$(short_sha_default)}"

SAFE_BUILD_NUMBER="$(printf '%s' "$PROJECT_BUILD_NUMBER" | tr -c '[:alnum:]._-' '-')"
SAFE_SHORT_SHA="$(printf '%s' "$PROJECT_GIT_SHA" | tr -c '[:alnum:]._-' '-')"

PRIMARY_IMAGE_TAG="${PROJECT_IMAGE_NAME}:${PROJECT_IMAGE_TAG}"
BUILD_IMAGE_TAG="${PROJECT_IMAGE_NAME}:build-${SAFE_BUILD_NUMBER}"
SHA_IMAGE_TAG="${PROJECT_IMAGE_NAME}:sha-${SAFE_SHORT_SHA}"

echo "Building release image:"
echo "  ${PRIMARY_IMAGE_TAG}"
echo "  ${BUILD_IMAGE_TAG}"
echo "  ${SHA_IMAGE_TAG}"
echo "  version: ${PROJECT_VERSION}"
echo "  build number: ${PROJECT_BUILD_NUMBER}"
echo "  git sha: ${PROJECT_GIT_SHA}"

docker build \
    --build-arg BUILD_NUMBER="${PROJECT_BUILD_NUMBER}" \
    --build-arg VERSION="${PROJECT_VERSION}" \
    -t "${PRIMARY_IMAGE_TAG}" \
    -t "${BUILD_IMAGE_TAG}" \
    -t "${SHA_IMAGE_TAG}" \
    -f "$PROJECT_DOCKERFILE_PATH" \
    "$REPO_DIR"

echo "Release build complete."
echo "Push with the GitHub Actions release workflow after review."
