"""Ryot integration client."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Type

from searcharr_nxg.domain.decision_model import RyotState
from searcharr_nxg.http import HttpJsonClient


METADATA_SEARCH_QUERY = """
query MetadataSearch($input: MetadataSearchInput!) {
  metadataSearch(input: $input) {
    response {
      items
      details {
        totalItems
      }
    }
  }
}
"""

METADATA_DETAILS_QUERY = """
query MetadataDetails($metadataId: String!) {
  metadataDetails(metadataId: $metadataId) {
    response {
      id
      title
      identifier
      lot
      source
      publishYear
    }
  }
}
"""

USER_METADATA_DETAILS_QUERY = """
query UserMetadataDetails($metadataId: String!) {
  userMetadataDetails(metadataId: $metadataId) {
    response {
      hasInteracted
      seenByUserCount
      history {
        state
        finishedOn
        lastUpdatedOn
      }
      collections {
        details {
          collectionName
        }
      }
    }
  }
}
"""


@dataclass(frozen=True)
class RyotMovieRecord:
    """Normalized Ryot movie state for a single title."""

    state: RyotState
    metadata_id: Optional[str]
    title: Optional[str]
    identifier: Optional[str]
    seen_by_user_count: int
    last_finished_on: Optional[str]
    has_interacted: bool
    collection_names: List[str]


@dataclass(frozen=True)
class RyotSeriesRecord:
    """Normalized Ryot series state for a single title."""

    state: RyotState
    metadata_id: Optional[str]
    title: Optional[str]
    identifier: Optional[str]
    seen_by_user_count: int
    last_finished_on: Optional[str]
    has_interacted: bool
    collection_names: List[str]


class RyotClient:
    """Ryot GraphQL client focused on movie inspection."""

    def __init__(
        self,
        url: str,
        api_key: str,
        *,
        graphql_path: str = "/backend/graphql",
        verify_ssl: bool = True,
        timeout_seconds: int = 15,
    ) -> None:
        self.http = HttpJsonClient(
            timeout_seconds=timeout_seconds,
            verify_ssl=verify_ssl,
        )
        self.api_key = api_key
        self.endpoint = f"{url.rstrip('/')}{graphql_path}"

    def inspect_movie(self, title: str, *, tmdb_id: Optional[int] = None) -> RyotMovieRecord:
        return self._inspect_media(
            title,
            tmdb_id=tmdb_id,
            lot="MOVIE",
            record_type=RyotMovieRecord,
        )

    def inspect_series(self, title: str, *, tmdb_id: Optional[int] = None) -> RyotSeriesRecord:
        """Inspect one series in Ryot using the TMDB show identifier when available."""

        return self._inspect_media(
            title,
            tmdb_id=tmdb_id,
            lot="SHOW",
            record_type=RyotSeriesRecord,
        )

    def _search_metadata_ids(self, title: str, *, lot: str) -> List[str]:
        payload = self._graphql(
            METADATA_SEARCH_QUERY,
            {
                "input": {
                    "lot": lot,
                    "source": "TMDB",
                    "search": {"query": title, "page": 1, "take": 5},
                }
            },
        )
        return list(
            (((payload.get("metadataSearch") or {}).get("response") or {}).get("items"))
            or []
        )

    def _inspect_media(
        self,
        title: str,
        *,
        tmdb_id: Optional[int],
        lot: str,
        record_type: Type[RyotMovieRecord] | Type[RyotSeriesRecord],
    ) -> RyotMovieRecord | RyotSeriesRecord:
        metadata_ids = self._search_metadata_ids(title, lot=lot)
        matched = None

        for metadata_id in metadata_ids:
            details = self._metadata_details(metadata_id)
            identifier = details.get("identifier")
            if tmdb_id is None or str(identifier) == str(tmdb_id):
                matched = details
                break

        if matched is None:
            return record_type(
                state=RyotState.NOT_IN_RYOT,
                metadata_id=None,
                title=None,
                identifier=None,
                seen_by_user_count=0,
                last_finished_on=None,
                has_interacted=False,
                collection_names=[],
            )

        user_details = self._user_metadata_details(matched["id"])
        history = user_details.get("history") or []
        collections = user_details.get("collections") or []
        seen_by_user_count = int(user_details.get("seenByUserCount") or 0)
        completed_history = [
            item for item in history if item.get("state") == "COMPLETED"
        ]
        collection_names = [
            (((item or {}).get("details") or {}).get("collectionName"))
            for item in collections
        ]
        collection_names = [name for name in collection_names if name]
        last_finished_on = None
        if completed_history:
            ordered = sorted(
                completed_history,
                key=lambda item: item.get("finishedOn") or item.get("lastUpdatedOn") or "",
            )
            last_finished_on = ordered[-1].get("finishedOn") or ordered[-1].get("lastUpdatedOn")

        if completed_history or seen_by_user_count > 0:
            state = RyotState.IN_RYOT_WATCHED
        else:
            state = RyotState.IN_RYOT_NOT_WATCHED

        return record_type(
            state=state,
            metadata_id=matched["id"],
            title=matched.get("title"),
            identifier=matched.get("identifier"),
            seen_by_user_count=seen_by_user_count,
            last_finished_on=last_finished_on,
            has_interacted=bool(user_details.get("hasInteracted")),
            collection_names=collection_names,
        )

    def _metadata_details(self, metadata_id: str) -> dict:
        payload = self._graphql(
            METADATA_DETAILS_QUERY,
            {"metadataId": metadata_id},
        )
        return ((payload.get("metadataDetails") or {}).get("response") or {})

    def _user_metadata_details(self, metadata_id: str) -> dict:
        payload = self._graphql(
            USER_METADATA_DETAILS_QUERY,
            {"metadataId": metadata_id},
        )
        return ((payload.get("userMetadataDetails") or {}).get("response") or {})

    def _graphql(self, query: str, variables: dict) -> dict:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = self.http.post(
            self.endpoint,
            headers=headers,
            json_body={"query": query, "variables": variables},
        )
        if payload.get("errors"):
            message = "; ".join(error.get("message", "Unknown GraphQL error") for error in payload["errors"])
            raise RuntimeError(f"Ryot GraphQL query failed: {message}")
        return payload.get("data") or {}
