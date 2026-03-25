"""Sonarr integration client scaffold."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Union

from searcharr_nxg.http import HttpJsonClient


@dataclass(frozen=True)
class SonarrOption:
    """Named Sonarr option such as a profile, root folder, or tag."""

    id: int
    name: str
    raw: dict


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
