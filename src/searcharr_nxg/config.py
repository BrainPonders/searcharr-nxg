"""Configuration loading helpers for Searcharr-nxg."""

from __future__ import annotations

from dataclasses import dataclass
import importlib.util
import os
from pathlib import Path
from types import ModuleType
from typing import Dict, Optional


REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class LoadedSettings:
    """Loaded settings module with its resolved path."""

    path: Path
    module: ModuleType


def resolve_settings_path(explicit_path: Optional[str] = None) -> Path:
    """Resolve a settings.py location from CLI, env, or common local paths."""

    candidates = []

    if explicit_path:
        candidates.append(Path(explicit_path))

    env_path = os.environ.get("SEARCHARR_SETTINGS_FILE")
    if env_path:
        candidates.append(Path(env_path))

    candidates.extend(
        [
            Path.cwd() / "settings.py",
            REPO_ROOT / "settings.py",
        ]
    )

    seen = set()
    for candidate in candidates:
        resolved = candidate.expanduser()
        key = str(resolved)
        if key in seen:
            continue
        seen.add(key)
        if resolved.is_file():
            return resolved.resolve()

    raise FileNotFoundError(
        "Could not find settings.py. Provide --settings-file, set SEARCHARR_SETTINGS_FILE, or create settings.py in the working tree."
    )


def load_settings(explicit_path: Optional[str] = None) -> LoadedSettings:
    """Load settings.py as an importable module."""

    path = resolve_settings_path(explicit_path)
    spec = importlib.util.spec_from_file_location("searcharr_nxg_settings", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to create import spec for settings.py")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return LoadedSettings(path=path, module=module)


def integration_summary(settings_module: ModuleType) -> Dict[str, bool]:
    """Return the enabled integration surface from the settings module."""

    return {
        "telegram": bool(getattr(settings_module, "tgram_token", "")),
        "tmdb": bool(getattr(settings_module, "tmdb_api_key", "")),
        "ryot": bool(getattr(settings_module, "ryot_enabled", False)),
        "radarr": bool(getattr(settings_module, "radarr_enabled", False)),
        "sonarr": bool(getattr(settings_module, "sonarr_enabled", False)),
    }
