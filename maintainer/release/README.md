# RELEASING

Maintainer guide for preparing and publishing project releases.

## Purpose

- keep the tracked release process concise
- separate local release helpers from project policy
- make it explicit which parts of the template must be customized

## Included Helpers

- `maintainer/release/release.sh`
  - builds local release-tagged container images
- `maintainer/release/update_available_versions.py`
  - optional helper for the release table in `README.md` and the image example in `docker/compose/.env.example`

Both helpers are templates. Review registry names, tag policy, release channels, and publication rules before using them in a real project.

## Current Project State

Searcharr-nxg now has a tag-driven GitHub release path for published container images.

- public image publishing targets `ghcr.io/brainponders/searcharr-nxg`
- release tags are expected to follow:
  - `vMAJOR.MINOR.PATCH`
  - `vMAJOR.MINOR.PATCH-rc.N`
  - `vMAJOR.MINOR.PATCH-dev.N`
- `latest` is intentionally not used
- the release workflow also refreshes the public version table in `README.md`

The local release helper still matters for validation, but the normal publication path is now GitHub Actions.

Current temporary publication limitation:

- published images are `linux/amd64` only
- `linux/arm64` publishing is temporarily disabled because the `11notes/python:3.12` arm64 build crashes under QEMU during dependency installation

## Local Preflight

1. Rebuild locally.
2. Run maintainer smoke checks.
3. Confirm the container, compose examples, and public docs still match the actual project.
4. Confirm the release tag and publish target match repository policy.

## Common Adaptation Points

- image name and registry
- release tag model
- CI workflow names
- public release table format
- immutable tag policy

## Useful Environment Variables

- `PROJECT_IMAGE_NAME`
- `PROJECT_IMAGE_TAG`
- `PROJECT_VERSION`
- `PROJECT_BUILD_NUMBER`
- `PROJECT_GIT_SHA`
- `PROJECT_IMAGE_REPO`

## Safety Rules

- Do not assume the default tag parser matches the real project.
- Do not publish `latest` unless the project explicitly chooses that policy.
- Keep project-specific release rules here, not in `.local/`.
