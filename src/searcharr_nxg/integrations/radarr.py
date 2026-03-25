"""Radarr integration client."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Union

from searcharr_nxg.domain.decision_model import RadarrState
from searcharr_nxg.http import HttpJsonClient, IntegrationError


@dataclass(frozen=True)
class RadarrMovieRecord:
    """Normalized Radarr movie state."""

    state: RadarrState
    title: Optional[str]
    monitored: bool
    has_file: bool
    quality_profile_id: Optional[int]
    quality_profile_name: Optional[str]
    minimum_availability: Optional[str]
    folder_path: Optional[str]
    tags: List[int]
    raw_quality: Optional[str]
    size_bytes: Optional[int]
    previously_owned: bool
    is_excluded: bool


@dataclass(frozen=True)
class RadarrOption:
    """Named Radarr option such as a profile, root folder, or tag."""

    id: int
    name: str
    raw: dict


@dataclass(frozen=True)
class RadarrActionResponse:
    """Normalized response from a write-side Radarr operation."""

    action: str
    movie_id: Optional[int]
    changed: bool
    payload: dict


class RadarrClient:
    """Small subset of the Radarr API needed for inspection and actions."""

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

    def inspect_movie(
        self,
        tmdb_id: int,
        *,
        previously_owned_tag: Optional[str] = None,
    ) -> RadarrMovieRecord:
        movie = self._find_movie_by_tmdb_id(tmdb_id)
        excluded = self._is_excluded(tmdb_id)

        if movie is None:
            return RadarrMovieRecord(
                state=RadarrState.NOT_IN_RADARR,
                title=None,
                monitored=False,
                has_file=False,
                quality_profile_id=None,
                quality_profile_name=None,
                minimum_availability=None,
                folder_path=None,
                tags=[],
                raw_quality=None,
                size_bytes=None,
                previously_owned=False,
                is_excluded=excluded,
            )

        monitored = bool(movie.get("monitored"))
        has_file = bool(movie.get("hasFile") or movie.get("movieFile"))
        quality_profile_id = movie.get("qualityProfileId")
        tag_ids = list(movie.get("tags") or [])
        tag_names = self._tag_names_for_ids(tag_ids)
        file_block = movie.get("movieFile") or {}
        quality_block = ((file_block.get("quality") or {}).get("quality") or {})

        if has_file and monitored:
            state = RadarrState.MONITORED_PRESENT
        elif has_file and not monitored:
            state = RadarrState.UNMONITORED_PRESENT
        elif not has_file and monitored:
            state = RadarrState.MONITORED_MISSING
        else:
            state = RadarrState.UNMONITORED_MISSING

        previously_owned = False
        if previously_owned_tag:
            previously_owned = previously_owned_tag.lower() in {
                name.lower() for name in tag_names
            }

        return RadarrMovieRecord(
            state=state,
            title=movie.get("title"),
            monitored=monitored,
            has_file=has_file,
            quality_profile_id=quality_profile_id,
            quality_profile_name=self._quality_profile_name(quality_profile_id),
            minimum_availability=movie.get("minimumAvailability"),
            folder_path=movie.get("rootFolderPath") or movie.get("path"),
            tags=tag_ids,
            raw_quality=quality_block.get("name"),
            size_bytes=file_block.get("size"),
            previously_owned=previously_owned,
            is_excluded=excluded,
        )

    def get_movie(self, movie_id: int) -> dict:
        """Fetch a full Radarr movie payload."""

        return self._get(f"movie/{movie_id}")

    def lookup_movie(self, tmdb_id: int) -> dict:
        """Resolve a TMDB movie into the Radarr lookup payload required for add."""

        payload = self._get("movie/lookup", params={"term": f"tmdb:{tmdb_id}"})
        for item in payload or []:
            if int(item.get("tmdbId") or 0) == tmdb_id:
                return item
        raise IntegrationError(f"Radarr lookup did not return TMDB id {tmdb_id}.")

    def list_quality_profiles(self) -> List[RadarrOption]:
        """Return all Radarr quality profiles."""

        payload = self._get("qualityProfile")
        return [
            RadarrOption(id=int(item["id"]), name=item["name"], raw=item)
            for item in payload or []
        ]

    def list_root_folders(self) -> List[RadarrOption]:
        """Return all Radarr root folders."""

        payload = self._get("rootFolder")
        return [
            RadarrOption(id=int(item["id"]), name=item["path"], raw=item)
            for item in payload or []
        ]

    def list_tags(self) -> List[RadarrOption]:
        """Return all Radarr tags."""

        payload = self._get("tag")
        return [
            RadarrOption(id=int(item["id"]), name=item["label"], raw=item)
            for item in payload or []
        ]

    def resolve_quality_profile(
        self, value: Union[str, int, None]
    ) -> Optional[RadarrOption]:
        """Resolve a quality profile by id or name."""

        if value is None:
            return None
        return self._match_option(self.list_quality_profiles(), value)

    def resolve_root_folder(
        self, value: Union[str, int, None]
    ) -> Optional[RadarrOption]:
        """Resolve a root folder by id or path."""

        if value is None:
            return None
        return self._match_option(self.list_root_folders(), value)

    def resolve_tag(self, value: Union[str, int, None]) -> Optional[RadarrOption]:
        """Resolve a tag by id or label."""

        if value is None:
            return None
        return self._match_option(self.list_tags(), value)

    def add_movie(
        self,
        *,
        tmdb_id: int,
        quality_profile_id: int,
        root_folder_path: str,
        minimum_availability: str,
        monitored: bool,
        search: bool,
        tag_ids: Optional[List[int]] = None,
    ) -> RadarrActionResponse:
        """Add a movie to Radarr using the lookup payload."""

        lookup = self.lookup_movie(tmdb_id)
        payload = {
            "tmdbId": lookup["tmdbId"],
            "title": lookup["title"],
            "year": lookup.get("year"),
            "qualityProfileId": quality_profile_id,
            "titleSlug": lookup["titleSlug"],
            "images": lookup.get("images") or [],
            "rootFolderPath": root_folder_path,
            "monitored": monitored,
            "minimumAvailability": minimum_availability,
            "tags": tag_ids or [],
            "addOptions": {"searchForMovie": search},
        }
        response = self._post("movie", payload)
        movie_id = response.get("id")
        return RadarrActionResponse(
            action="add_movie",
            movie_id=movie_id,
            changed=True,
            payload=response,
        )

    def update_movie(
        self,
        movie_id: int,
        *,
        monitored: Optional[bool] = None,
        quality_profile_id: Optional[int] = None,
        minimum_availability: Optional[str] = None,
    ) -> RadarrActionResponse:
        """Update an existing Radarr movie."""

        payload = self.get_movie(movie_id)
        if monitored is not None:
            payload["monitored"] = monitored
        if quality_profile_id is not None:
            payload["qualityProfileId"] = quality_profile_id
        if minimum_availability is not None:
            payload["minimumAvailability"] = minimum_availability
        response = self._put(f"movie/{movie_id}", payload)
        return RadarrActionResponse(
            action="update_movie",
            movie_id=movie_id,
            changed=True,
            payload=response or payload,
        )

    def search_movie(self, movie_id: int) -> RadarrActionResponse:
        """Trigger a Radarr search for a movie."""

        payload = {"name": "MoviesSearch", "movieIds": [movie_id]}
        response = self._post("command", payload)
        return RadarrActionResponse(
            action="search_movie",
            movie_id=movie_id,
            changed=True,
            payload=response,
        )

    def _find_movie_by_tmdb_id(self, tmdb_id: int) -> Optional[dict]:
        try:
            payload = self._get("movie", params={"tmdbId": tmdb_id})
            if isinstance(payload, dict):
                payload = [payload]
        except IntegrationError:
            payload = self._get("movie")
        for item in payload or []:
            if int(item.get("tmdbId") or 0) == tmdb_id:
                return item
        return None

    def _is_excluded(self, tmdb_id: int) -> bool:
        try:
            payload = self._get("exclusions")
        except IntegrationError:
            return False
        for item in payload or []:
            if int(item.get("tmdbId") or 0) == tmdb_id:
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

    def _tag_names_for_ids(self, tag_ids: List[int]) -> List[str]:
        if not tag_ids:
            return []
        payload = self._get("tag")
        tag_map: Dict[int, str] = {item.get("id"): item.get("label") for item in payload or []}
        return [tag_map[tag_id] for tag_id in tag_ids if tag_id in tag_map]

    @staticmethod
    def _match_option(options: List[RadarrOption], value: Union[str, int]) -> Optional[RadarrOption]:
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
        headers = {"X-Api-Key": self.api_key}
        return self.http.post(url, headers=headers, json_body=payload)

    def _put(self, endpoint: str, payload: dict):
        url = f"{self.base_url}/api/v3/{endpoint}"
        headers = {"X-Api-Key": self.api_key}
        return self.http.put(url, headers=headers, json_body=payload)
