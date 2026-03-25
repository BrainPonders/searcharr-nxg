"""Text rendering helpers for Searcharr-nxg CLI and Telegram flows."""

from __future__ import annotations

from datetime import datetime
from html import escape
from typing import List

from searcharr_nxg.domain.decision_model import Action
from searcharr_nxg.services.movie_actions import MovieActionPreview
from searcharr_nxg.services.movie_inspection import MovieInspectionReport


ACTION_LABELS = {
    Action.ADD_MOVIE: "Add Movie",
    Action.ADD_AND_SEARCH: "Add + Search",
    Action.SEARCH_NOW: "Search Now",
    Action.CHANGE_PROFILE: "Change Profile",
    Action.UNMONITOR: "Unmonitor",
    Action.REMONITOR: "Re-monitor",
    Action.OPEN_IN_JELLYFIN: "Open in Jellyfin",
    Action.SEARCH_UPGRADE: "Search Upgrade",
}

RADARR_LABELS = {
    "A0": "Not in Radarr",
    "A1": "In Radarr, monitored, missing file",
    "A2": "In Radarr, unmonitored, missing file",
    "A3": "In Radarr, monitored, file present",
    "A4": "In Radarr, unmonitored, file present",
}


def _bool_label(value: bool) -> str:
    return "yes" if value else "no"


def _yes_no_upper(value: bool) -> str:
    return "YES" if value else "NO"


def _code(value: str) -> str:
    return f"<code>{escape(value)}</code>"


def _field(label: str, value: str) -> str:
    return f"<b>{escape(label)}:</b> {_code(value)}"


def _format_watch_status(count: int, last_finished_on: str | None) -> str:
    if count <= 0:
        return "Not watched"
    if last_finished_on:
        return f"{count}x | {_format_summary_datetime(last_finished_on)}"
    return f"{count}x"


def _format_ryot_collections(collection_names: List[str]) -> str:
    if collection_names:
        return " | ".join(collection_names)
    return "n/a"


def _format_summary_datetime(value: str) -> str:
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return value
    return parsed.strftime("%d-%b-%Y @ %H:%M")


def _format_availability(raw_quality: str | None, has_file: bool, size_bytes: int | None) -> str:
    if not has_file:
        return "Missing"
    size_label = _format_size(size_bytes)
    if raw_quality and size_label:
        return f"{raw_quality} ({size_label})"
    if raw_quality:
        return raw_quality
    if size_label:
        return size_label
    return "Available"


def _format_radarr_quality_summary(
    quality_profile_name: str | None,
    raw_quality: str | None,
    has_file: bool,
    size_bytes: int | None,
) -> tuple[str, ...]:
    profile = quality_profile_name or "n/a"
    availability = _format_availability(raw_quality, has_file, size_bytes)
    return (
        _field("Quality Profile", profile),
        _field("Available", availability),
    )


def _format_radarr_movie_summary(is_registered: bool, monitored: bool) -> str:
    if not is_registered:
        return "Not in Radarr"
    return "Monitored" if monitored else "Unmonitored"


def _format_radarr_status_summary(is_registered: bool, monitored: bool, is_excluded: bool) -> str:
    status = _format_radarr_movie_summary(is_registered, monitored)
    if is_excluded:
        return f"{status} | Excluded"
    return status


def _format_size(size_bytes: int | None) -> str | None:
    if not size_bytes:
        return None
    gib = size_bytes / (1024 ** 3)
    return f"{gib:.1f} GB"


def action_label(action: Action) -> str:
    """Return a human-readable label for a product action."""

    return ACTION_LABELS.get(action, action.value)


def render_movie_inspection(report: MovieInspectionReport) -> str:
    """Render a CLI-friendly movie inspection summary."""

    candidate = report.candidate
    lines: List[str] = [
        f"{candidate.title} ({candidate.year or 'Unknown year'})",
        "",
        "TMDB",
        f"- id: {candidate.tmdb_id}",
        f"- language: {candidate.original_language or 'unknown'}",
        "",
        "Ryot",
        f"- state: {report.ryot.state.value}",
        f"- found: {_bool_label(report.ryot.metadata_id is not None)}",
        f"- watched count: {report.ryot.seen_by_user_count}",
        f"- last watched: {_format_summary_datetime(report.ryot.last_finished_on) if report.ryot.last_finished_on else 'n/a'}",
        f"- collections: {', '.join(report.ryot.collection_names) if report.ryot.collection_names else 'n/a'}",
        "",
        "Radarr",
        f"- state: {report.radarr.state.value}",
        f"- monitored: {_bool_label(report.radarr.monitored)}",
        f"- file present: {_bool_label(report.radarr.has_file)}",
        f"- quality profile: {report.radarr.quality_profile_name or 'n/a'}",
        f"- current quality: {report.radarr.raw_quality or 'n/a'}",
        f"- previously owned: {_bool_label(report.radarr.previously_owned)}",
        f"- excluded: {_bool_label(report.radarr.is_excluded)}",
        "",
    ]

    if report.warning:
        lines.extend(["Warning", f"- {report.warning}", ""])

    lines.append("Actions")
    for action in report.actions:
        lines.append(f"- {action.value}")

    return "\n".join(lines)


def render_movie_inspection_message(report: MovieInspectionReport) -> str:
    """Render a compact formatted Orion-stack summary for Telegram."""

    candidate = report.candidate
    lines: List[str] = [f"<b>{escape(candidate.title)} ({candidate.year or 'Unknown year'})</b>"]

    if report.warning:
        lines.extend(["", f"<b>Warning</b>\n{escape(report.warning)}"])

    ryot_registered = report.ryot.metadata_id is not None
    radarr_registered = report.radarr.state.value != "A0"

    lines.extend(
        [
            "",
            _field("Ryot", "Registered" if ryot_registered else "Not registered"),
            _field("Watched", _format_watch_status(report.ryot.seen_by_user_count, report.ryot.last_finished_on)),
            _field("Collections", _format_ryot_collections(report.ryot.collection_names)),
            "",
            _field(
                "Radarr",
                _format_radarr_status_summary(
                    radarr_registered,
                    report.radarr.monitored,
                    report.radarr.is_excluded,
                ),
            ),
        ]
    )
    quality_lines = _format_radarr_quality_summary(
        report.radarr.quality_profile_name,
        report.radarr.raw_quality,
        report.radarr.has_file,
        report.radarr.size_bytes,
    )
    insertion_index = lines.index(
        _field(
            "Radarr",
            _format_radarr_status_summary(
                radarr_registered,
                report.radarr.monitored,
                report.radarr.is_excluded,
            ),
        )
    ) + 1
    for offset, line in enumerate(quality_lines):
        lines.insert(insertion_index + offset, line)

    if report.radarr.previously_owned:
        lines.append(_field("History", "Previously owned"))

    return "\n".join(lines)


def render_exclusion_override_message(report: MovieInspectionReport, action: Action) -> str:
    """Render the exclusion warning shown before add actions."""

    return "\n\n".join(
        [
            render_movie_inspection_message(report),
            (
                "<b>Radarr exclusion</b>\n"
                f"This movie is excluded in Radarr. List imports will ignore it, but you can still use <b><code>{escape(action_label(action))} Anyway</code></b> as a manual override."
            ),
        ]
    )


def render_candidate_browser_message(candidate, position: int, total: int) -> str:
    """Render the poster-browser caption for one TMDB candidate."""

    lines: List[str] = [
        f"<b>{escape(candidate.title)} ({candidate.year or 'Unknown year'})</b>",
        f"{position}/{total}",
    ]
    overview = (candidate.overview or "").strip().replace("\n", " ")
    if len(overview) > 220:
        overview = f"{overview[:217]}..."
    if overview:
        lines.extend(["", escape(overview)])
    return "\n".join(lines)


def render_profile_selection_message(report: MovieInspectionReport, action: Action) -> str:
    """Render the profile-selection prompt under the current summary."""

    return "\n\n".join(
        [
            render_movie_inspection_message(report),
            f"<b>Choose quality profile for {escape(action_label(action))}</b>",
        ]
    )


def render_movie_action_result_message(preview: MovieActionPreview) -> str:
    """Render a compact Telegram-friendly action result summary."""

    lines = [
        f"<b>Action</b>: {escape(action_label(preview.action))}",
        f"<b>Result</b>: {escape(preview.message)}",
    ]
    details = _summarize_action_details(preview)
    if details.get("movie_id") is not None:
        lines.append(f"<b>Movie id</b>: {details['movie_id']}")
    if details.get("command_name"):
        command = details["command_name"]
        if details.get("command_id") is not None:
            command = f"{command} (id {details['command_id']})"
        lines.append(f"<b>Command</b>: {escape(command)}")
    if details.get("status"):
        lines.append(f"<b>Status</b>: {escape(str(details['status']))}")
    return "\n".join(lines)


def render_movie_action_preview(preview: MovieActionPreview) -> str:
    """Render a CLI-friendly action preview or execution result."""

    lines: List[str] = [
        f"Action: {preview.action.value}",
        f"Allowed: {_bool_label(preview.allowed)}",
        f"Executed: {_bool_label(preview.execute)}",
        f"Message: {preview.message}",
    ]
    details = _summarize_action_details(preview)
    if details:
        lines.append("Details")
        for key in sorted(details):
            lines.append(f"- {key}: {details[key]}")
    return "\n".join(lines)


def _summarize_action_details(preview: MovieActionPreview) -> dict:
    if not preview.details:
        return {}
    if not preview.execute:
        return preview.details

    details = preview.details
    if details.get("name") == "MoviesSearch" or "movieIds" in details:
        summary = {}
        if details.get("id") is not None:
            summary["command_id"] = details["id"]
        if details.get("name"):
            summary["command_name"] = details["name"]
        if details.get("status"):
            summary["status"] = details["status"]
        if details.get("movieIds") is not None:
            summary["movie_ids"] = details["movieIds"]
        return summary or details

    summary = {}
    movie_id = details.get("id") or details.get("movieId")
    if movie_id is not None:
        summary["movie_id"] = movie_id
    if details.get("title"):
        summary["title"] = details["title"]
    if details.get("tmdbId") is not None:
        summary["tmdb_id"] = details["tmdbId"]
    if details.get("monitored") is not None:
        summary["monitored"] = details["monitored"]
    if details.get("qualityProfileId") is not None:
        summary["quality_profile_id"] = details["qualityProfileId"]
    if details.get("rootFolderPath"):
        summary["root_folder_path"] = details["rootFolderPath"]
    elif details.get("path"):
        summary["path"] = details["path"]
    has_file = details.get("hasFile")
    if has_file is None and isinstance(details.get("movieFile"), dict):
        has_file = True
    if has_file is not None:
        summary["has_file"] = has_file
    movie_file = details.get("movieFile") or {}
    quality = ((movie_file.get("quality") or {}).get("quality") or {}).get("name")
    if quality:
        summary["current_quality"] = quality
    return summary or details
