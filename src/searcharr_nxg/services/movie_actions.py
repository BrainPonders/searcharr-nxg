"""Preview-first movie action execution for Searcharr-nxg."""

from __future__ import annotations

from dataclasses import dataclass
from types import ModuleType
from typing import List, Optional

from searcharr_nxg.domain.decision_model import Action
from searcharr_nxg.integrations.radarr import RadarrActionResponse, RadarrClient, RadarrOption
from searcharr_nxg.services.movie_inspection import MovieInspectionReport


@dataclass(frozen=True)
class MovieActionPreview:
    """Preview or execution result for a requested movie action."""

    action: Action
    execute: bool
    allowed: bool
    message: str
    details: dict


def preview_or_execute_movie_action(
    *,
    action: Action,
    report: MovieInspectionReport,
    radarr_client: RadarrClient,
    settings_module: ModuleType,
    execute: bool = False,
    quality_profile: Optional[str] = None,
    root_folder: Optional[str] = None,
) -> MovieActionPreview:
    """Plan or execute a single movie action."""

    if action not in report.actions:
        return MovieActionPreview(
            action=action,
            execute=execute,
            allowed=False,
            message=f"Action {action.value} is not allowed for Radarr state {report.radarr.state.value}.",
            details={},
        )

    if action is Action.OPEN_IN_JELLYFIN:
        base_url = getattr(settings_module, "jellyfin_base_url", "")
        details = {"jellyfin_base_url": base_url or None}
        if not base_url:
            return MovieActionPreview(
                action=action,
                execute=execute,
                allowed=False,
                message="Jellyfin base URL is not configured.",
                details=details,
            )
        return MovieActionPreview(
            action=action,
            execute=execute,
            allowed=True,
            message="Jellyfin deep linking is not implemented yet.",
            details=details,
        )

    if action in (Action.ADD_MOVIE, Action.ADD_AND_SEARCH):
        quality_option = _select_quality_profile(
            radarr_client=radarr_client,
            settings_module=settings_module,
            explicit_value=quality_profile,
        )
        root_option = _select_root_folder(
            radarr_client=radarr_client,
            settings_module=settings_module,
            explicit_value=root_folder,
        )
        tag_ids = _forced_tag_ids(radarr_client, settings_module)
        details = {
            "tmdb_id": report.candidate.tmdb_id,
            "quality_profile_id": quality_option.id,
            "quality_profile_name": quality_option.name,
            "root_folder_path": root_option.name,
            "minimum_availability": getattr(
                settings_module, "radarr_min_availability", "released"
            ),
            "monitored": bool(getattr(settings_module, "radarr_add_monitored", True)),
            "search": action is Action.ADD_AND_SEARCH,
            "tag_ids": tag_ids,
        }
        if not execute:
            return MovieActionPreview(
                action=action,
                execute=False,
                allowed=True,
                message="Preview only. Use --execute to add the movie in Radarr.",
                details=details,
            )
        response = radarr_client.add_movie(
            tmdb_id=report.candidate.tmdb_id,
            quality_profile_id=quality_option.id,
            root_folder_path=root_option.name,
            minimum_availability=details["minimum_availability"],
            monitored=details["monitored"],
            search=details["search"],
            tag_ids=tag_ids,
        )
        return _from_radarr_response(
            action=action,
            message="Movie was added in Radarr.",
            response=response,
        )

    if report.radarr.state.value == "A0" or report.radarr.quality_profile_id is None:
        return MovieActionPreview(
            action=action,
            execute=execute,
            allowed=False,
            message="Radarr movie record is required for this action.",
            details={},
        )

    movie_id = _require_existing_movie_id(report, radarr_client)

    if action in (Action.SEARCH_NOW, Action.SEARCH_UPGRADE):
        details = {"movie_id": movie_id}
        if not execute:
            return MovieActionPreview(
                action=action,
                execute=False,
                allowed=True,
                message="Preview only. Use --execute to trigger a Radarr search.",
                details=details,
            )
        response = radarr_client.search_movie(movie_id)
        return _from_radarr_response(
            action=action,
            message="Radarr search command submitted.",
            response=response,
        )

    if action in (Action.UNMONITOR, Action.REMONITOR):
        monitored = action is Action.REMONITOR
        details = {"movie_id": movie_id, "monitored": monitored}
        if not execute:
            return MovieActionPreview(
                action=action,
                execute=False,
                allowed=True,
                message="Preview only. Use --execute to update monitored state in Radarr.",
                details=details,
            )
        response = radarr_client.update_movie(movie_id, monitored=monitored)
        return _from_radarr_response(
            action=action,
            message="Radarr monitored state updated.",
            response=response,
        )

    if action is Action.CHANGE_PROFILE:
        quality_option = _select_quality_profile(
            radarr_client=radarr_client,
            settings_module=settings_module,
            explicit_value=quality_profile,
        )
        details = {
            "movie_id": movie_id,
            "quality_profile_id": quality_option.id,
            "quality_profile_name": quality_option.name,
        }
        if not execute:
            return MovieActionPreview(
                action=action,
                execute=False,
                allowed=True,
                message="Preview only. Use --execute to change the Radarr quality profile.",
                details=details,
            )
        response = radarr_client.update_movie(
            movie_id,
            quality_profile_id=quality_option.id,
        )
        return _from_radarr_response(
            action=action,
            message="Radarr quality profile updated.",
            response=response,
        )

    return MovieActionPreview(
        action=action,
        execute=execute,
        allowed=False,
        message=f"Action {action.value} is not implemented yet.",
        details={},
    )


def _from_radarr_response(
    *,
    action: Action,
    message: str,
    response: RadarrActionResponse,
) -> MovieActionPreview:
    return MovieActionPreview(
        action=action,
        execute=True,
        allowed=True,
        message=message,
        details=response.payload,
    )


def resolve_quality_profile_choices(
    *,
    radarr_client: RadarrClient,
    settings_module: ModuleType,
) -> List[RadarrOption]:
    """Return the quality profiles available for interactive selection."""

    configured = list(getattr(settings_module, "radarr_quality_profile_id", []))
    if configured:
        options: List[RadarrOption] = []
        for value in configured:
            option = radarr_client.resolve_quality_profile(value)
            if option is None:
                raise RuntimeError(f"Could not resolve Radarr quality profile: {value}")
            options.append(option)
        return options
    return radarr_client.list_quality_profiles()


def _select_quality_profile(
    *,
    radarr_client: RadarrClient,
    settings_module: ModuleType,
    explicit_value: Optional[str],
) -> RadarrOption:
    value = explicit_value
    if value is None:
        choices = resolve_quality_profile_choices(
            radarr_client=radarr_client,
            settings_module=settings_module,
        )
        if len(choices) != 1:
            raise RuntimeError(
                "A quality profile must be specified when more than one profile is configured."
            )
        value = str(choices[0].id)
    option = radarr_client.resolve_quality_profile(value)
    if option is None:
        raise RuntimeError(f"Could not resolve Radarr quality profile: {value}")
    return option


def _select_root_folder(
    *,
    radarr_client: RadarrClient,
    settings_module: ModuleType,
    explicit_value: Optional[str],
) -> RadarrOption:
    value = explicit_value
    configured = list(getattr(settings_module, "radarr_movie_paths", []))
    if value is None:
        if len(configured) == 1:
            value = str(configured[0])
        elif len(configured) > 1:
            raise RuntimeError(
                "A root folder must be specified when more than one movie path is configured."
            )
        else:
            options = radarr_client.list_root_folders()
            if not options:
                raise RuntimeError("No Radarr root folders were found.")
            return options[0]
    option = radarr_client.resolve_root_folder(value)
    if option is None:
        raise RuntimeError(f"Could not resolve Radarr root folder: {value}")
    return option


def _forced_tag_ids(radarr_client: RadarrClient, settings_module: ModuleType) -> List[int]:
    tag_ids: List[int] = []
    for tag_value in getattr(settings_module, "radarr_forced_tags", []):
        option = radarr_client.resolve_tag(tag_value)
        if option is None:
            raise RuntimeError(f"Could not resolve Radarr tag: {tag_value}")
        tag_ids.append(option.id)
    return tag_ids


def _require_existing_movie_id(
    report: MovieInspectionReport,
    radarr_client: RadarrClient,
) -> int:
    movie = radarr_client._find_movie_by_tmdb_id(report.candidate.tmdb_id)
    if movie is None or movie.get("id") is None:
        raise RuntimeError("Could not resolve the existing Radarr movie id.")
    return int(movie["id"])
