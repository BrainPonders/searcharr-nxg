"""TMDB integration client."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import List, Optional

from searcharr_nxg.http import HttpJsonClient


@dataclass(frozen=True)
class TmdbMovieCandidate:
    """Minimal TMDB movie candidate used by Searcharr-nxg."""

    tmdb_id: int
    title: str
    release_date: Optional[str]
    overview: str
    original_language: Optional[str]
    poster_path: Optional[str]

    @property
    def poster_url(self) -> Optional[str]:
        """Return the fully qualified TMDB poster URL when available."""

        if not self.poster_path:
            return None
        return f"https://image.tmdb.org/t/p/w500{self.poster_path}"

    @property
    def year(self) -> Optional[int]:
        if not self.release_date:
            return None
        try:
            return int(self.release_date[:4])
        except ValueError:
            return None

    @property
    def tmdb_web_url(self) -> str:
        return f"https://www.themoviedb.org/movie/{self.tmdb_id}"


@dataclass(frozen=True)
class TmdbSeriesCandidate:
    """Minimal TMDB TV-series candidate used by Searcharr-nxg."""

    tmdb_id: int
    title: str
    first_air_date: Optional[str]
    overview: str
    original_language: Optional[str]
    poster_path: Optional[str]
    tvdb_id: Optional[int] = None

    @property
    def poster_url(self) -> Optional[str]:
        if not self.poster_path:
            return None
        return f"https://image.tmdb.org/t/p/w500{self.poster_path}"

    @property
    def year(self) -> Optional[int]:
        if not self.first_air_date:
            return None
        try:
            return int(self.first_air_date[:4])
        except ValueError:
            return None

    @property
    def tmdb_web_url(self) -> str:
        return f"https://www.themoviedb.org/tv/{self.tmdb_id}"


class TmdbClient:
    """Client for TMDB search and movie details."""

    def __init__(
        self,
        api_key: str,
        *,
        language: str = "en-US",
        auth_mode: str = "auto",
        verify_ssl: bool = True,
        timeout_seconds: int = 15,
    ) -> None:
        self.api_key = api_key
        self.language = language
        self.auth_mode = auth_mode
        self.http = HttpJsonClient(
            timeout_seconds=timeout_seconds,
            verify_ssl=verify_ssl,
        )
        self.base_url = "https://api.themoviedb.org/3"

    def search_movies(
        self,
        query: str,
        *,
        limit: int = 20,
        primary_release_year: Optional[int] = None,
    ) -> List[TmdbMovieCandidate]:
        """Search TMDB and prefer newer feature-film results over extras."""

        raw_results = self._search_movie_payload(
            query,
            page=1,
            primary_release_year=primary_release_year,
        )
        results = list(raw_results.get("results", []))
        total_pages = int(raw_results.get("total_pages") or 1)

        # Pull a few additional pages so broad titles like "Batman" don't stop at
        # the first relevance-ranked page, then rank locally for poster browsing.
        target_pool = max(limit * 3, 20)
        for page in range(2, min(total_pages, 4) + 1):
            if len(results) >= target_pool:
                break
            page_payload = self._search_movie_payload(
                query,
                page=page,
                primary_release_year=primary_release_year,
            )
            results.extend(page_payload.get("results", []))

        if primary_release_year is not None and not results:
            return self.search_movies(query, limit=limit, primary_release_year=None)

        preferred = [item for item in results if self._is_preferred_movie_result(item)]
        fallback = [item for item in results if not self._is_preferred_movie_result(item)]
        ranked = self._sort_movie_results(
            preferred,
            primary_release_year=primary_release_year,
        ) + self._sort_movie_results(
            fallback,
            primary_release_year=primary_release_year,
        )
        deduped = self._dedupe_by_tmdb_id(ranked)
        return [self._parse_candidate(item) for item in deduped[:limit]]

    def get_movie(self, tmdb_id: int) -> TmdbMovieCandidate:
        payload = self.http.get(
            f"{self.base_url}/movie/{tmdb_id}",
            headers=self._build_auth_headers(),
            params={
                **self._build_auth_params(),
                "language": self.language,
            },
        )
        return self._parse_candidate(payload)

    def search_series(
        self,
        query: str,
        *,
        limit: int = 20,
        first_air_date_year: Optional[int] = None,
    ) -> List[TmdbSeriesCandidate]:
        """Search TMDB TV results and rank them for poster browsing."""

        raw_results = self._search_tv_payload(
            query,
            page=1,
            first_air_date_year=first_air_date_year,
        )
        results = list(raw_results.get("results", []))
        total_pages = int(raw_results.get("total_pages") or 1)

        target_pool = max(limit * 3, 20)
        for page in range(2, min(total_pages, 4) + 1):
            if len(results) >= target_pool:
                break
            page_payload = self._search_tv_payload(
                query,
                page=page,
                first_air_date_year=first_air_date_year,
            )
            results.extend(page_payload.get("results", []))

        ranked = self._sort_series_results(
            self._dedupe_by_tmdb_id(results),
            first_air_date_year=first_air_date_year,
        )
        return [self._parse_series_candidate(item) for item in ranked[:limit]]

    def get_series(self, tmdb_id: int) -> TmdbSeriesCandidate:
        payload = self.http.get(
            f"{self.base_url}/tv/{tmdb_id}",
            headers=self._build_auth_headers(),
            params={
                **self._build_auth_params(),
                "language": self.language,
                "append_to_response": "external_ids",
            },
        )
        return self._parse_series_candidate(payload)

    def _search_movie_payload(
        self,
        query: str,
        *,
        page: int,
        primary_release_year: Optional[int] = None,
    ) -> dict:
        return self.http.get(
            f"{self.base_url}/search/movie",
            headers=self._build_auth_headers(),
            params={
                **self._build_auth_params(),
                "language": self.language,
                "query": query,
                "include_adult": "false",
                "page": str(page),
                **(
                    {"primary_release_year": str(primary_release_year)}
                    if primary_release_year is not None
                    else {}
                ),
            },
        )

    def _search_tv_payload(
        self,
        query: str,
        *,
        page: int,
        first_air_date_year: Optional[int] = None,
    ) -> dict:
        return self.http.get(
            f"{self.base_url}/search/tv",
            headers=self._build_auth_headers(),
            params={
                **self._build_auth_params(),
                "language": self.language,
                "query": query,
                "include_adult": "false",
                "page": str(page),
                **(
                    {"first_air_date_year": str(first_air_date_year)}
                    if first_air_date_year is not None
                    else {}
                ),
            },
        )

    def _build_auth_headers(self) -> Optional[dict]:
        if self._uses_bearer_token():
            return {
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json",
            }
        return None

    def _build_auth_params(self) -> dict:
        if self._uses_bearer_token():
            return {}
        return {"api_key": self.api_key}

    def _uses_bearer_token(self) -> bool:
        if self.auth_mode == "v4":
            return True
        if self.auth_mode == "v3":
            return False
        return bool(re.match(r"^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$", self.api_key))

    @staticmethod
    def _is_preferred_movie_result(item: dict) -> bool:
        title = (item.get("title") or item.get("name") or "").lower()
        overview = (item.get("overview") or "").lower()
        genre_ids = set(item.get("genre_ids") or [])

        if 16 in genre_ids or 99 in genre_ids:
            return False
        if item.get("video") is True:
            return False

        extra_markers = (
            "making of",
            "behind the scenes",
            "featurette",
            "documentary",
            "interview",
            "trailer",
        )
        haystack = f"{title} {overview}"
        return not any(marker in haystack for marker in extra_markers)

    @staticmethod
    def _sort_movie_results(
        results: List[dict],
        *,
        primary_release_year: Optional[int] = None,
    ) -> List[dict]:
        def sort_key(item: dict):
            release_date = item.get("release_date") or ""
            year = 0
            if len(release_date) >= 4 and release_date[:4].isdigit():
                year = int(release_date[:4])
            popularity = float(item.get("popularity") or 0.0)
            vote_count = int(item.get("vote_count") or 0)
            if primary_release_year is not None:
                return (-abs(year - primary_release_year), year, release_date, popularity, vote_count)
            return (year, release_date, popularity, vote_count)

        return sorted(results, key=sort_key, reverse=True)

    @staticmethod
    def _dedupe_by_tmdb_id(results: List[dict]) -> List[dict]:
        seen = set()
        deduped = []
        for item in results:
            tmdb_id = int(item.get("id") or 0)
            if not tmdb_id or tmdb_id in seen:
                continue
            seen.add(tmdb_id)
            deduped.append(item)
        return deduped

    @staticmethod
    def _sort_series_results(
        results: List[dict],
        *,
        first_air_date_year: Optional[int] = None,
    ) -> List[dict]:
        def sort_key(item: dict):
            first_air_date = item.get("first_air_date") or ""
            year = 0
            if len(first_air_date) >= 4 and first_air_date[:4].isdigit():
                year = int(first_air_date[:4])
            popularity = float(item.get("popularity") or 0.0)
            vote_count = int(item.get("vote_count") or 0)
            if first_air_date_year is not None:
                return (-abs(year - first_air_date_year), year, first_air_date, popularity, vote_count)
            return (year, first_air_date, popularity, vote_count)

        return sorted(results, key=sort_key, reverse=True)

    @staticmethod
    def _parse_candidate(item: dict) -> TmdbMovieCandidate:
        return TmdbMovieCandidate(
            tmdb_id=int(item["id"]),
            title=item.get("title") or item.get("name") or "Unknown title",
            release_date=item.get("release_date"),
            overview=item.get("overview") or "",
            original_language=item.get("original_language"),
            poster_path=item.get("poster_path"),
        )

    @staticmethod
    def _parse_series_candidate(item: dict) -> TmdbSeriesCandidate:
        external_ids = item.get("external_ids") or {}
        tvdb_id = external_ids.get("tvdb_id") or item.get("tvdb_id")
        return TmdbSeriesCandidate(
            tmdb_id=int(item["id"]),
            title=item.get("name") or item.get("title") or "Unknown title",
            first_air_date=item.get("first_air_date"),
            overview=item.get("overview") or "",
            original_language=item.get("original_language"),
            poster_path=item.get("poster_path"),
            tvdb_id=int(tvdb_id) if tvdb_id not in (None, "") else None,
        )
