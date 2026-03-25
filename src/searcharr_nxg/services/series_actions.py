"""Preview-first series action execution for Searcharr-nxg."""

from __future__ import annotations

from dataclasses import dataclass
from types import ModuleType
from typing import List, Optional

from searcharr_nxg.domain.decision_model import Action
from searcharr_nxg.integrations.sonarr import SonarrActionResponse, SonarrClient, SonarrOption
from searcharr_nxg.services.series_inspection import SeriesInspectionReport


@dataclass(frozen=True)
class SeriesActionPreview:
    """Preview or execution result for a requested series action."""

    action: Action
    execute: bool
    allowed: bool
    message: str
    details: dict


def preview_or_execute_series_action(
    *,
    action: Action,
    report: SeriesInspectionReport,
    sonarr_client: SonarrClient,
    settings_module: ModuleType,
    execute: bool = False,
    quality_profile: Optional[str] = None,
    root_folder: Optional[str] = None,
) -> SeriesActionPreview:
    """Plan or execute a single series action."""

    if action not in report.actions:
        return SeriesActionPreview(
            action=action,
            execute=execute,
            allowed=False,
            message=f"Action {action.value} is not allowed for Sonarr state {report.sonarr.state.value}.",
            details={},
        )

    if action in (Action.ADD_MOVIE, Action.ADD_AND_SEARCH):
        quality_option = _select_quality_profile(
            sonarr_client=sonarr_client,
            settings_module=settings_module,
            explicit_value=quality_profile,
        )
        root_option = _select_root_folder(
            sonarr_client=sonarr_client,
            settings_module=settings_module,
            explicit_value=root_folder,
        )
        tag_ids = _forced_tag_ids(sonarr_client, settings_module)
        details = {
            "tmdb_id": report.candidate.tmdb_id,
            "tvdb_id": report.candidate.tvdb_id,
            "quality_profile_id": quality_option.id,
            "quality_profile_name": quality_option.name,
            "root_folder_path": root_option.name,
            "monitored": bool(getattr(settings_module, "sonarr_add_monitored", True)),
            "search": action is Action.ADD_AND_SEARCH,
            "tag_ids": tag_ids,
        }
        if not execute:
            return SeriesActionPreview(
                action=action,
                execute=False,
                allowed=True,
                message="Preview only. Use --execute to add the series in Sonarr.",
                details=details,
            )
        response = sonarr_client.add_series(
            tvdb_id=report.candidate.tvdb_id,
            tmdb_id=report.candidate.tmdb_id,
            quality_profile_id=quality_option.id,
            root_folder_path=root_option.name,
            monitored=details["monitored"],
            search=details["search"],
            tag_ids=tag_ids,
        )
        return _from_sonarr_response(
            action=action,
            message="Series was added in Sonarr.",
            response=response,
        )

    if report.sonarr.state.value == "S0" or report.sonarr.quality_profile_id is None:
        return SeriesActionPreview(
            action=action,
            execute=execute,
            allowed=False,
            message="Sonarr series record is required for this action.",
            details={},
        )

    series_id = _require_existing_series_id(report, sonarr_client)

    if action is Action.SEARCH_NOW:
        details = {"series_id": series_id}
        if not execute:
            return SeriesActionPreview(
                action=action,
                execute=False,
                allowed=True,
                message="Preview only. Use --execute to trigger a Sonarr search.",
                details=details,
            )
        response = sonarr_client.search_series(series_id)
        return _from_sonarr_response(
            action=action,
            message="Sonarr search command submitted.",
            response=response,
        )

    if action in (Action.UNMONITOR, Action.REMONITOR):
        monitored = action is Action.REMONITOR
        details = {"series_id": series_id, "monitored": monitored}
        if not execute:
            return SeriesActionPreview(
                action=action,
                execute=False,
                allowed=True,
                message="Preview only. Use --execute to update monitored state in Sonarr.",
                details=details,
            )
        response = sonarr_client.update_series(series_id, monitored=monitored)
        return _from_sonarr_response(
            action=action,
            message="Sonarr monitored state updated.",
            response=response,
        )

    if action is Action.CHANGE_PROFILE:
        quality_option = _select_quality_profile(
            sonarr_client=sonarr_client,
            settings_module=settings_module,
            explicit_value=quality_profile,
        )
        details = {
            "series_id": series_id,
            "quality_profile_id": quality_option.id,
            "quality_profile_name": quality_option.name,
        }
        if not execute:
            return SeriesActionPreview(
                action=action,
                execute=False,
                allowed=True,
                message="Preview only. Use --execute to change the Sonarr quality profile.",
                details=details,
            )
        response = sonarr_client.update_series(
            series_id,
            quality_profile_id=quality_option.id,
        )
        return _from_sonarr_response(
            action=action,
            message="Sonarr quality profile updated.",
            response=response,
        )

    return SeriesActionPreview(
        action=action,
        execute=execute,
        allowed=False,
        message=f"Action {action.value} is not implemented yet.",
        details={},
    )


def _from_sonarr_response(
    *,
    action: Action,
    message: str,
    response: SonarrActionResponse,
) -> SeriesActionPreview:
    return SeriesActionPreview(
        action=action,
        execute=True,
        allowed=True,
        message=message,
        details=response.payload,
    )


def resolve_quality_profile_choices(
    *,
    sonarr_client: SonarrClient,
    settings_module: ModuleType,
) -> List[SonarrOption]:
    """Return the quality profiles available for interactive series selection."""

    configured = list(getattr(settings_module, "sonarr_quality_profile_id", []))
    if configured:
        options: List[SonarrOption] = []
        for value in configured:
            option = sonarr_client.resolve_quality_profile(value)
            if option is None:
                raise RuntimeError(f"Could not resolve Sonarr quality profile: {value}")
            options.append(option)
        return options
    return sonarr_client.list_quality_profiles()


def _select_quality_profile(
    *,
    sonarr_client: SonarrClient,
    settings_module: ModuleType,
    explicit_value: Optional[str],
) -> SonarrOption:
    value = explicit_value
    if value is None:
        choices = resolve_quality_profile_choices(
            sonarr_client=sonarr_client,
            settings_module=settings_module,
        )
        if len(choices) != 1:
            raise RuntimeError(
                "A quality profile must be specified when more than one Sonarr profile is configured."
            )
        value = str(choices[0].id)
    option = sonarr_client.resolve_quality_profile(value)
    if option is None:
        raise RuntimeError(f"Could not resolve Sonarr quality profile: {value}")
    return option


def _select_root_folder(
    *,
    sonarr_client: SonarrClient,
    settings_module: ModuleType,
    explicit_value: Optional[str],
) -> SonarrOption:
    value = explicit_value
    configured = list(getattr(settings_module, "sonarr_series_paths", []))
    if value is None:
        if len(configured) == 1:
            value = str(configured[0])
        elif len(configured) > 1:
            raise RuntimeError(
                "A root folder must be specified when more than one series path is configured."
            )
        else:
            options = sonarr_client.list_root_folders()
            if not options:
                raise RuntimeError("No Sonarr root folders were found.")
            return options[0]
    option = sonarr_client.resolve_root_folder(value)
    if option is None:
        raise RuntimeError(f"Could not resolve Sonarr root folder: {value}")
    return option


def _forced_tag_ids(sonarr_client: SonarrClient, settings_module: ModuleType) -> List[int]:
    tag_ids: List[int] = []
    for tag_value in getattr(settings_module, "sonarr_forced_tags", []):
        option = sonarr_client.resolve_tag(tag_value)
        if option is None:
            raise RuntimeError(f"Could not resolve Sonarr tag: {tag_value}")
        tag_ids.append(option.id)
    return tag_ids


def _require_existing_series_id(
    report: SeriesInspectionReport,
    sonarr_client: SonarrClient,
) -> int:
    series = sonarr_client._find_series(
        tvdb_id=report.candidate.tvdb_id,
        tmdb_id=report.candidate.tmdb_id,
    )
    if series is None or series.get("id") is None:
        raise RuntimeError("Could not resolve the existing Sonarr series id.")
    return int(series["id"])
