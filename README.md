<p><em>Ryot-centric Telegram control layer for Radarr and Sonarr.</em></p>

![GitHub release](https://img.shields.io/github/v/release/brainponders/searcharr-nxg)
![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/brainponders/searcharr-nxg/release.yml?label=release)
[![License](https://img.shields.io/github/license/BrainPonders/searcharr-nxg)](LICENSE)
![GitHub stars](https://img.shields.io/github/stars/brainponders/searcharr-nxg)

<br>

# Searcharr-nxg

Searcharr-nxg is a Telegram-driven request system for movie and series automation. It originated from the Searcharr idea space, but is now reworked around a Ryot-first decision model and a cleaner standalone project structure. Instead of treating Radarr or Sonarr as the main source of truth, Searcharr-nxg starts each decision from Ryot, combines that long-term history with current Arr state, and then exposes deliberate actions such as add, re-monitor, search now, or change profile.

The result is a stricter and more context-aware request flow:
- warn when something was already watched
- surface whether a title is currently in Radarr or Sonarr
- keep exclusions visible without blocking intentional manual overrides
- present the current quality profile and availability before an action is taken

<br>

### Why use Searcharr-nxg?

Searcharr-nxg fills the gap between media history and media execution:

- **Ryot-first decisions:** watched state and selected collections are checked before an action is shown
- **Current Arr visibility:** monitored state, profile, file availability, and exclusions are surfaced up front
- **Telegram-first control:** poster browsing and action buttons are often faster than opening the Arr UI for each request

<br>

## Architecture

Searcharr-nxg currently consists of a Python backend with Telegram as the user interface.

```text
┌────────────────────────────────────┐
│          Telegram Bot UI           │
│ Poster browser · Summary · Actions │
└──────────────────┬─────────────────┘
                   │
┌──────────────────▼─────────────────┐
│          Searcharr-nxg             │
│ Decision model · Runtime           │
│ Ryot lookup · TMDB lookup          │
│ Radarr / Sonarr action routing     │
└───────────────┬───────────┬────────┘
                │           │
      ┌─────────▼──────┐ ┌──▼──────────┐
      │      Ryot      │ │    TMDB     │
      │ History / tags │ │ Search data │
      └────────────────┘ └─────────────┘
                │
     ┌──────────▼──────────┐
     │  Radarr / Sonarr    │
     │ Execution + state   │
     └─────────────────────┘
```

**Technology Stack**

```text
Application:
├── Python 3.12
├── python-telegram-bot
├── requests
└── unittest

Integrations:
├── Ryot GraphQL API
├── TMDB API
├── Radarr API
└── Sonarr API

Container:
└── 11notes/python:3.12
```

---

<!-- BEGIN: AVAILABLE_VERSIONS -->
## Available Versions

This optional section is updated from Git tags.
Edit or replace the helper if the project uses a different release model.

| Channel | Current tag | Deployment value |
| --- | --- | --- |
| Stable | `v1.0.0` | `PROJECT_IMAGE=ghcr.io/brainponders/searcharr-nxg:v1.0.0` |
| Release Candidate | - | - |
| Development | - | - |
<!-- END: AVAILABLE_VERSIONS -->

---

## Installation

This guide describes a Docker Compose deployment. The published image is built on the [11notes Python](https://github.com/11notes/docker-python) base image and is intended to run with a pinned tag, not `latest`.

Searcharr-nxg does not expose a public web UI. The main runtime interface is the Telegram bot, while `settings.py` defines how the container reaches Ryot, TMDB, Radarr, and Sonarr.

---

#### 1. Create deployment folder

```bash
mkdir -p ~/searcharr-nxg
cd ~/searcharr-nxg
mkdir -p config data
```

Set permissions:

```bash
chown -R 1000:1000 config data
chmod -R u+rwX,go-rwx config data
```

---

#### 2. Create `docker-compose.yml`

Create `~/searcharr-nxg/docker-compose.yml` with:

```yaml
services:
  app:
    image: ${PROJECT_IMAGE}
    container_name: ${PROJECT_CONTAINER_NAME:-searcharr-nxg}
    restart: unless-stopped

    env_file:
      - .env

    environment:
      SEARCHARR_SETTINGS_FILE: /app/settings.py

    volumes:
      - "${PROJECT_SETTINGS_FILE:-./config/settings.py}:/app/settings.py:ro"
      - ./data:/app/data
```

If your Arr and Ryot services are reachable on a shared Docker network, add the matching `networks:` section here.

---

#### 3. Create `.env`

Create `~/searcharr-nxg/.env` with at least:

```env
PROJECT_IMAGE=ghcr.io/brainponders/searcharr-nxg:v1.0.0
PROJECT_CONTAINER_NAME=searcharr-nxg
PROJECT_SETTINGS_FILE=./config/settings.py
```

> [!WARNING]
> Always use an explicit image tag from the `Available Versions` table above.

---

#### 4. Create `config/settings.py`

Copy the sample settings file and edit it for your environment:

```bash
cp /path/to/repo/settings-sample.py ~/searcharr-nxg/config/settings.py
```

At minimum, configure Telegram, TMDB, Ryot, and Radarr. Add Sonarr as well if series support is enabled.

Searcharr-nxg expects this settings file to remain local and private. Do not commit it.

---

#### 5. Start Searcharr-nxg

```bash
cd ~/searcharr-nxg
docker compose up -d
docker compose logs -f app
```

The container starts the `searcharr-nxg` command by default. If `tgram_token` is configured, the Telegram bot starts automatically.

---

## Environment Variables

| Variable | Description | Example |
| --- | --- | --- |
| `PROJECT_IMAGE` | Pinned Searcharr-nxg image tag | `ghcr.io/brainponders/searcharr-nxg:v1.0.0` |
| `PROJECT_CONTAINER_NAME` | Container name override | `searcharr-nxg` |
| `PROJECT_SETTINGS_FILE` | Local settings bind mount source | `./config/settings.py` |
| `SEARCHARR_SETTINGS_FILE` | In-container settings path | `/app/settings.py` |

---

## First-time validation

1. Start the container and confirm the expected integrations appear in the log.
2. In Telegram, use `/start`.
3. Test `/movie <title>`.
4. Test `/series <title>`.
5. Confirm the summary shows Ryot state plus the relevant Radarr or Sonarr state before you execute an action.

---

## Repository Layout

- `src/searcharr_nxg/` contains the Python package, integrations, runtime, and Telegram bot code
- `documentation/` contains product and governance documentation
- `maintainer/` contains the tracked maintainer workflow, Docker assets, and release scripts
- `docker/compose/` contains public runtime examples
- `lang/` contains retained upstream language resources from the Searcharr lineage
- `.local/` is the local-only safety bucket and is never committed

---

## Release Workflow

Releases are intended to be tag-driven.

- Create a Git tag following one of these formats:
  - `vMAJOR.MINOR.PATCH`
  - `vMAJOR.MINOR.PATCH-rc.N`
  - `vMAJOR.MINOR.PATCH-dev.N`
- Push the tag to GitHub
- The GitHub Actions release workflow will:
  - build the container image
  - publish it to `ghcr.io/brainponders/searcharr-nxg`
  - create a GitHub release
  - refresh the `Available Versions` section and `docker/compose/.env.example`

`latest` is intentionally not published.

Current temporary limitation:
- published images are `linux/amd64` only
- `linux/arm64` publishing is temporarily disabled because the `11notes/python:3.12` arm64 build crashes under QEMU during dependency installation

---

## Reference Lineage

Searcharr-nxg originated from Searcharr lineage, but it is now treated as a standalone project with its own architecture and release path.

- historical baseline: `toddrob99/searcharr`

That repository remains useful as a selective reference input, but Searcharr-nxg is no longer maintained as a direct fork continuation.
