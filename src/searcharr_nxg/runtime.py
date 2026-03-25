"""Shared runtime helpers used by the CLI and Telegram bot."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace
import re
from types import ModuleType
from typing import Iterable, Optional, Sequence

from searcharr_nxg.domain.decision_model import Action
from searcharr_nxg.integrations.radarr import RadarrClient
from searcharr_nxg.integrations.ryot import RyotClient
from searcharr_nxg.integrations.sonarr import SonarrClient
from searcharr_nxg.integrations.tmdb import TmdbClient, TmdbMovieCandidate
from searcharr_nxg.services.movie_actions import MovieActionPreview, preview_or_execute_movie_action
from searcharr_nxg.services.movie_inspection import MovieInspectionReport, build_movie_inspection_report


@dataclass(frozen=True)
class SearcharrRuntime:
    """Configured application runtime for movie inspection and actions."""

    settings_module: ModuleType
    tmdb_client: TmdbClient
    radarr_client: Optional[RadarrClient]
    ryot_client: Optional[RyotClient]
    sonarr_client: Optional[SonarrClient]

    @classmethod
    def from_settings(cls, settings_module: ModuleType) -> "SearcharrRuntime":
        """Build a runtime from the current settings module."""

        timeout_seconds = int(getattr(settings_module, "requests_timeout_seconds", 15))
        tmdb_api_key = getattr(settings_module, "tmdb_api_key", "")
        if not tmdb_api_key:
            raise RuntimeError("tmdb_api_key is required for movie inspection.")

        tmdb_client = TmdbClient(
            tmdb_api_key,
            language=getattr(settings_module, "tmdb_language", "en-US"),
            auth_mode=getattr(settings_module, "tmdb_auth_mode", "auto"),
            verify_ssl=bool(getattr(settings_module, "tmdb_verify_ssl", True)),
            timeout_seconds=timeout_seconds,
        )

        radarr_client = None
        if getattr(settings_module, "radarr_enabled", False):
            radarr_url = getattr(settings_module, "radarr_url", "")
            radarr_api_key = getattr(settings_module, "radarr_api_key", "")
            if radarr_url and radarr_api_key:
                radarr_client = RadarrClient(
                    radarr_url,
                    radarr_api_key,
                    verify_ssl=bool(getattr(settings_module, "radarr_verify_ssl", True)),
                    timeout_seconds=timeout_seconds,
                )

        ryot_client = None
        if getattr(settings_module, "ryot_enabled", False):
            ryot_url = getattr(settings_module, "ryot_url", "")
            ryot_api_key = getattr(settings_module, "ryot_api_key", "")
            if ryot_url and ryot_api_key:
                ryot_client = RyotClient(
                    ryot_url,
                    ryot_api_key,
                    graphql_path=getattr(settings_module, "ryot_graphql_path", "/backend/graphql"),
                    verify_ssl=bool(getattr(settings_module, "ryot_verify_ssl", True)),
                    timeout_seconds=timeout_seconds,
                )

        sonarr_client = None
        if getattr(settings_module, "sonarr_enabled", False):
            sonarr_url = getattr(settings_module, "sonarr_url", "")
            sonarr_api_key = getattr(settings_module, "sonarr_api_key", "")
            if sonarr_url and sonarr_api_key:
                sonarr_client = SonarrClient(
                    sonarr_url,
                    sonarr_api_key,
                    verify_ssl=bool(getattr(settings_module, "sonarr_verify_ssl", True)),
                    timeout_seconds=timeout_seconds,
                )

        return cls(
            settings_module=settings_module,
            tmdb_client=tmdb_client,
            radarr_client=radarr_client,
            ryot_client=ryot_client,
            sonarr_client=sonarr_client,
        )

    def search_movie_candidates(self, query: str, *, limit: int = 20) -> Sequence[TmdbMovieCandidate]:
        """Search TMDB for movie candidates."""

        query = query.strip()
        if not query:
            raise RuntimeError("A non-empty movie query is required.")
        normalized_query, primary_release_year = _extract_query_year(query)
        return self.tmdb_client.search_movies(
            normalized_query,
            limit=limit,
            primary_release_year=primary_release_year,
        )

    def inspect_movie_query(
        self,
        query: str,
        *,
        candidate_index: int = 1,
    ) -> MovieInspectionReport:
        """Inspect a movie by TMDB search query."""

        candidates = list(self.search_movie_candidates(query, limit=20))
        if not candidates:
            raise RuntimeError("No TMDB movie candidates were found for the provided query.")
        if candidate_index < 1 or candidate_index > len(candidates):
            raise RuntimeError(
                f"candidate index {candidate_index} is out of range for {len(candidates)} TMDB results."
            )
        return self._build_report(candidates[candidate_index - 1])

    def inspect_tmdb_movie(self, tmdb_id: int) -> MovieInspectionReport:
        """Inspect a movie by TMDB id."""

        candidate = self.tmdb_client.get_movie(tmdb_id)
        return self._build_report(candidate)

    def perform_movie_action(
        self,
        *,
        tmdb_id: int,
        action: Action,
        execute: bool = False,
        quality_profile: Optional[str] = None,
        root_folder: Optional[str] = None,
    ) -> MovieActionPreview:
        """Preview or execute a Radarr-backed movie action."""

        if self.radarr_client is None:
            raise RuntimeError("Radarr must be enabled to perform movie actions.")
        report = self.inspect_tmdb_movie(tmdb_id)
        return preview_or_execute_movie_action(
            action=action,
            report=report,
            radarr_client=self.radarr_client,
            settings_module=self.settings_module,
            execute=execute,
            quality_profile=quality_profile,
            root_folder=root_folder,
        )

    def _build_report(self, candidate: TmdbMovieCandidate) -> MovieInspectionReport:
        radarr_record = None
        if self.radarr_client is not None:
            radarr_record = self.radarr_client.inspect_movie(
                candidate.tmdb_id,
                previously_owned_tag=getattr(
                    self.settings_module, "radarr_previously_owned_tag", None
                ),
            )

        ryot_record = None
        if self.ryot_client is not None:
            ryot_record = self.ryot_client.inspect_movie(candidate.title, tmdb_id=candidate.tmdb_id)
            ryot_record = replace(
                ryot_record,
                collection_names=_filter_collection_names(
                    ryot_record.collection_names,
                    getattr(
                        self.settings_module,
                        "ryot_visible_collections",
                        ["Owned", "Completed", "In Progress"],
                    ),
                ),
            )

        return build_movie_inspection_report(
            candidate,
            ryot=ryot_record,
            radarr=radarr_record,
        )


def _extract_query_year(query: str) -> tuple[str, Optional[int]]:
    match = re.match(r"^(.*?)(?:[\s(]+)((?:19|20)\d{2})\)?\s*$", query.strip())
    if match is None:
        return query, None
    title = match.group(1).strip()
    year = int(match.group(2))
    return title or query, year


def _filter_collection_names(
    collection_names: Sequence[str],
    allowed_names: Optional[Iterable[str]],
) -> list[str]:
    if allowed_names is None:
        return list(collection_names)
    normalized = {
        str(name).strip().casefold()
        for name in allowed_names
        if str(name).strip()
    }
    if not normalized:
        return []
    return [name for name in collection_names if name.strip().casefold() in normalized]
