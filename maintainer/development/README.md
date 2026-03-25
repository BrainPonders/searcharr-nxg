# DEVELOPMENT

Maintainer guide for local rebuilds and local runtime validation.

## Purpose

- bootstrap the Python package locally
- build a local container image from the current working tree
- prepare a separate dev runtime folder outside the repository
- preserve local `.env`, compose, and settings files instead of overwriting them

## Script Boundary

`maintainer/development/dev-build.sh` is a template helper. Review and adapt these assumptions before relying on it:

- the repository root is resolved from `../..`
- the Dockerfile lives at `maintainer/docker/Dockerfile`
- the runtime folder defaults to `<repo-parent>/<project-slug>-dev/`
- the runtime env file uses `PROJECT_IMAGE=` as the image reference key
- the runtime settings file lives at `config/settings.py` in the generated dev runtime

## Runtime Layout

Default runtime folder:

- `<repo-parent>/<project-slug>-dev/`

Default runtime files:

- `docker-compose.yml`
- `.env`
- `config/settings.py`
- `data/`

Template sources:

- `docker/compose/docker-compose-dev.yml.example`
- `docker/compose/.env.dev.example`
- `settings-sample.py`

## First Run

1. Create a local virtual environment if needed.
2. Install the package with `pip install -e .`.
3. Copy `settings-sample.py` to `settings.py` if you want to run the package directly from the repository.
4. Run `searcharr-nxg --dry-run` to validate bootstrap-level wiring.
5. Review `docker/compose/docker-compose-dev.yml.example` and `docker/compose/.env.dev.example`.
6. Run `bash maintainer/development/dev-build.sh` to build the image and prepare the external runtime folder.
7. Edit the generated runtime `config/settings.py` and `.env` before starting the dev container for real work.

## Useful Environment Variables

- `PROJECT_SLUG`
- `PROJECT_IMAGE_NAME`
- `PROJECT_DEV_PROJECT`
- `PROJECT_DEV_ROOT`
- `PROJECT_DOCKERFILE_PATH`
- `PROJECT_DEV_UP`

## Safety Rules

- The script should not overwrite an existing runtime `.env`.
- The script should not overwrite an existing runtime compose file.
- The script should not overwrite an existing runtime `config/settings.py`.
- The script should not write secrets into the repository.
- The script is only a starting point and should be tightened per project.
