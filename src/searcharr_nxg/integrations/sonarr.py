"""Sonarr integration client scaffold."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Union

from searcharr_nxg.domain.decision_model import SonarrState
from searcharr_nxg.http import HttpJsonClient, IntegrationError


@dataclass(frozen=True)
class SonarrOption:
    """Named Sonarr option such as a profile, root folder, or tag."""

    id: int
    name: str
    raw: dict


@dataclass(frozen=True)
class SonarrSeriesRecord:
    """Normalized Sonarr series state."""

    state: SonarrState
    title: Optional[str]
    monitored: bool
    has_files: bool
    quality_profile_id: Optional[int]
    quality_profile_name: Optional[str]
    folder_path: Optional[str]
    tags: List[int]
    size_bytes: Optional[int]
    episode_file_count: int
    episode_count: int
    is_excluded: bool


@dataclass(frozen=True)
class SonarrActionResponse:
    """Normalized response from a write-side Sonarr operation."""

    action: str
    series_id: Optional[int]
    changed: bool
    payload: dict


class SonarrClient:
    """Small subset of the Sonarr API needed for configuration-backed workflows."""

    def __init__(
        self,
        url: str,
        api_key: str,
        *,
        timeout_seconds: int = 15,
        verify_ssl: bool = True,
    ) -> None:
        self.http = HttpJsonClient(
            timeout_seconds=timeout_seconds,
            verify_ssl=verify_ssl,
        )
        self.api_key = api_key
        self.base_url = url.rstrip("/")

    def list_quality_profiles(self) -> List[SonarrOption]:
        """Return all Sonarr quality profiles."""

        payload = self._get("qualityProfile")
        return [
            SonarrOption(id=int(item["id"]), name=item["name"], raw=item)
            for item in payload or []
        ]

    def list_root_folders(self) -> List[SonarrOption]:
        """Return all Sonarr root folders."""

        payload = self._get("rootFolder")
        return [
            SonarrOption(id=int(item["id"]), name=item["path"], raw=item)
            for item in payload or []
        ]

    def list_tags(self) -> List[SonarrOption]:
        """Return all Sonarr tags."""

        payload = self._get("tag")
        return [
            SonarrOption(id=int(item["id"]), name=item["label"], raw=item)
            for item in payload or []
        ]

    def inspect_series(self, *, tvdb_id: Optional[int], tmdb_id: Optional[int] = None) -> SonarrSeriesRecord:
        """Inspect a series by TVDB id with TMDB fallback when available."""

        series = self._find_series(tvdb_id=tvdb_id, tmdb_id=tmdb_id)
        excluded = self._is_excluded(tvdb_id=tvdb_id, tmdb_id=tmdb_id)
        if series is None:
            return SonarrSeriesRecord(
                state=SonarrState.NOT_IN_SONARR,
                title=None,
                monitored=False,
                has_files=False,
                quality_profile_id=None,
                quality_profile_name=None,
                folder_path=None,
                tags=[],
                size_bytes=None,
                episode_file_count=0,
                episode_count=0,
                is_excluded=excluded,
            )

        monitored = bool(series.get("monitored"))
        statistics = series.get("statistics") or {}
        episode_file_count = int(statistics.get("episodeFileCount") or 0)
        episode_count = int(
            statistics.get("episodeCount")
            or statistics.get("totalEpisodeCount")
            or 0
        )
        has_files = episode_file_count > 0 or bool(statistics.get("sizeOnDisk"))
        if has_files and monitored:
            state = SonarrState.MONITORED_PRESENT
        elif has_files and not monitored:
            state = SonarrState.UNMONITORED_PRESENT
        elif not has_files and monitored:
            state = SonarrState.MONITORED_MISSING
        else:
            state = SonarrState.UNMONITORED_MISSING

        quality_profile_id = series.get("qualityProfileId")
        return SonarrSeriesRecord(
            state=state,
            title=series.get("title"),
            monitored=monitored,
            has_files=has_files,
            quality_profile_id=quality_profile_id,
            quality_profile_name=self._quality_profile_name(quality_profile_id),
            folder_path=series.get("rootFolderPath") or series.get("path"),
            tags=list(series.get("tags") or []),
            size_bytes=statistics.get("sizeOnDisk"),
            episode_file_count=episode_file_count,
            episode_count=episode_count,
            is_excluded=excluded,
        )

    def get_series(self, series_id: int) -> dict:
        """Fetch a full Sonarr series payload."""

        return self._get(f"series/{series_id}")

    def lookup_series(self, *, tvdb_id: Optional[int], tmdb_id: Optional[int] = None) -> dict:
        """Resolve a TVDB or TMDB series identifier using Sonarr lookup."""

        if tvdb_id is not None:
            payload = self._get("series/lookup", params={"term": f"tvdb:{tvdb_id}"})
        elif tmdb_id is not None:
            payload = self._get("series/lookup", params={"term": f"tmdb:{tmdb_id}"})
        else:
            raise IntegrationError("Sonarr lookup requires a tvdb_id or tmdb_id.")
        for item in payload or []:
            if tvdb_id is not None and int(item.get("tvdbId") or 0) == tvdb_id:
                return item
            if tmdb_id is not None and int(item.get("tmdbId") or 0) == tmdb_id:
                return item
        raise IntegrationError("Sonarr lookup did not return the requested series.")

    def resolve_quality_profile(
        self, value: Union[str, int, None]
    ) -> Optional[SonarrOption]:
        """Resolve a Sonarr quality profile by id or name."""

        if value is None:
            return None
        return self._match_option(self.list_quality_profiles(), value)

    def resolve_root_folder(
        self, value: Union[str, int, None]
    ) -> Optional[SonarrOption]:
        """Resolve a Sonarr root folder by id or path."""

        if value is None:
            return None
        return self._match_option(self.list_root_folders(), value)

    def resolve_tag(self, value: Union[str, int, None]) -> Optional[SonarrOption]:
        """Resolve a Sonarr tag by id or label."""

        if value is None:
            return None
        return self._match_option(self.list_tags(), value)

    def add_series(
        self,
        *,
        tvdb_id: Optional[int],
        tmdb_id: Optional[int],
        quality_profile_id: int,
        root_folder_path: str,
        monitored: bool,
        search: bool,
        tag_ids: Optional[List[int]] = None,
    ) -> SonarrActionResponse:
        """Add a series to Sonarr using the lookup payload."""

        lookup = self.lookup_series(tvdb_id=tvdb_id, tmdb_id=tmdb_id)
        payload = dict(lookup)
        payload.pop("id", None)
        payload["qualityProfileId"] = quality_profile_id
        payload["rootFolderPath"] = root_folder_path
        payload["monitored"] = monitored
        payload["tags"] = tag_ids or []
        payload["addOptions"] = {"searchForMissingEpisodes": search}
        response = self._post("series", payload)
        series_id = response.get("id")
        return SonarrActionResponse(
            action="add_series",
            series_id=series_id,
            changed=True,
            payload=response,
        )

    def update_series(
        self,
        series_id: int,
        *,
        monitored: Optional[bool] = None,
        quality_profile_id: Optional[int] = None,
    ) -> SonarrActionResponse:
        """Update an existing Sonarr series."""

        payload = self.get_series(series_id)
        if monitored is not None:
            payload["monitored"] = monitored
        if quality_profile_id is not None:
            payload["qualityProfileId"] = quality_profile_id
        response = self._put(f"series/{series_id}", payload)
        return SonarrActionResponse(
            action="update_series",
            series_id=series_id,
            changed=True,
            payload=response or payload,
        )

    def search_series(self, series_id: int) -> SonarrActionResponse:
        """Trigger a Sonarr search for a series."""

        payload = {"name": "SeriesSearch", "seriesId": series_id}
        response = self._post("command", payload)
        return SonarrActionResponse(
            action="search_series",
            series_id=series_id,
            changed=True,
            payload=response,
        )

    def _find_series(self, *, tvdb_id: Optional[int], tmdb_id: Optional[int]) -> Optional[dict]:
        try:
            payload = self._get("series")
        except IntegrationError:
            return None
        for item in payload or []:
            if tvdb_id is not None and int(item.get("tvdbId") or 0) == tvdb_id:
                return item
            if tmdb_id is not None and int(item.get("tmdbId") or 0) == tmdb_id:
                return item
        return None

    def _is_excluded(self, *, tvdb_id: Optional[int], tmdb_id: Optional[int]) -> bool:
        try:
            payload = self._get("exclusions")
        except Exception:
            return False
        for item in payload or []:
            if tvdb_id is not None and int(item.get("tvdbId") or 0) == tvdb_id:
                return True
            if tmdb_id is not None and int(item.get("tmdbId") or 0) == tmdb_id:
                return True
        return False

    def _quality_profile_name(self, quality_profile_id: Optional[int]) -> Optional[str]:
        if quality_profile_id is None:
            return None
        payload = self._get("qualityProfile")
        for item in payload or []:
            if item.get("id") == quality_profile_id:
                return item.get("name")
        return None

    @staticmethod
    def _match_option(options: List[SonarrOption], value: Union[str, int]) -> Optional[SonarrOption]:
        value_str = str(value)
        for option in options:
            if value_str == str(option.id) or value_str.lower() == option.name.lower():
                return option
        return None

    def _get(self, endpoint: str, *, params: Optional[dict] = None):
        url = f"{self.base_url}/api/v3/{endpoint}"
        headers = {"X-Api-Key": self.api_key}
        return self.http.get(url, headers=headers, params=params)

    def _post(self, endpoint: str, payload: dict):
        url = f"{self.base_url}/api/v3/{endpoint}"
        headers = {
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json",
        }
        return self.http.post(url, headers=headers, json_body=payload)

    def _put(self, endpoint: str, payload: dict):
        url = f"{self.base_url}/api/v3/{endpoint}"
        headers = {
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json",
        }
        return self.http.put(url, headers=headers, json_body=payload)
