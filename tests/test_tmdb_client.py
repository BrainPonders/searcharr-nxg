"""Tests for TMDB client auth handling."""

from __future__ import annotations

import unittest

from searcharr_nxg.integrations.tmdb import TmdbClient


class _FakeHttp:
    def __init__(self, payloads):
        self.payloads = payloads
        self.calls = []
        self.params = []

    def get(self, url, *, headers=None, params=None):
        page = int((params or {}).get("page", "1"))
        self.calls.append(page)
        self.params.append(params or {})
        return self.payloads[page]


class TmdbClientTests(unittest.TestCase):
    def test_v4_bearer_token_is_auto_detected(self) -> None:
        client = TmdbClient(
            "aaa.bbb.ccc",
            timeout_seconds=15,
        )
        self.assertEqual(client._build_auth_params(), {})
        self.assertEqual(
            client._build_auth_headers(),
            {
                "Authorization": "Bearer aaa.bbb.ccc",
                "Accept": "application/json",
            },
        )

    def test_v3_key_uses_query_parameter(self) -> None:
        client = TmdbClient(
            "plain-v3-key",
            timeout_seconds=15,
        )
        self.assertEqual(client._build_auth_headers(), None)
        self.assertEqual(client._build_auth_params(), {"api_key": "plain-v3-key"})

    def test_auth_mode_can_force_v4(self) -> None:
        client = TmdbClient(
            "plain-v4-token-without-dots",
            auth_mode="v4",
            timeout_seconds=15,
        )
        self.assertEqual(client._build_auth_params(), {})
        self.assertEqual(
            client._build_auth_headers(),
            {
                "Authorization": "Bearer plain-v4-token-without-dots",
                "Accept": "application/json",
            },
        )

    def test_search_prefers_newer_feature_films(self) -> None:
        client = TmdbClient("plain-v3-key", timeout_seconds=15)
        client.http = _FakeHttp(
            {
                1: {
                    "total_pages": 2,
                    "results": [
                        {
                            "id": 1,
                            "title": "Batman",
                            "release_date": "1989-06-23",
                            "overview": "",
                            "original_language": "en",
                            "poster_path": None,
                            "genre_ids": [28],
                            "popularity": 20,
                            "vote_count": 10,
                            "video": False,
                        },
                        {
                            "id": 2,
                            "title": "Batman: Making Of",
                            "release_date": "2024-01-01",
                            "overview": "Documentary featurette",
                            "original_language": "en",
                            "poster_path": None,
                            "genre_ids": [99],
                            "popularity": 30,
                            "vote_count": 5,
                            "video": False,
                        },
                    ],
                },
                2: {
                    "total_pages": 2,
                    "results": [
                        {
                            "id": 3,
                            "title": "The Batman",
                            "release_date": "2022-03-01",
                            "overview": "",
                            "original_language": "en",
                            "poster_path": None,
                            "genre_ids": [80, 28],
                            "popularity": 80,
                            "vote_count": 100,
                            "video": False,
                        },
                        {
                            "id": 4,
                            "title": "Batman Beyond",
                            "release_date": "2025-07-01",
                            "overview": "",
                            "original_language": "en",
                            "poster_path": None,
                            "genre_ids": [16, 28],
                            "popularity": 90,
                            "vote_count": 50,
                            "video": False,
                        },
                    ],
                },
            }
        )

        results = client.search_movies("batman", limit=3)

        self.assertEqual([item.tmdb_id for item in results], [3, 1, 4])
        self.assertEqual(client.http.calls, [1, 2])

    def test_search_filters_documentary_video_results_last(self) -> None:
        client = TmdbClient("plain-v3-key", timeout_seconds=15)
        client.http = _FakeHttp(
            {
                1: {
                    "total_pages": 1,
                    "results": [
                        {
                            "id": 11,
                            "title": "Office Space",
                            "release_date": "1999-02-19",
                            "overview": "",
                            "original_language": "en",
                            "poster_path": None,
                            "genre_ids": [35],
                            "popularity": 40,
                            "vote_count": 100,
                            "video": False,
                        },
                        {
                            "id": 12,
                            "title": "Office Space Trailer",
                            "release_date": "2025-01-01",
                            "overview": "Trailer",
                            "original_language": "en",
                            "poster_path": None,
                            "genre_ids": [35],
                            "popularity": 60,
                            "vote_count": 10,
                            "video": True,
                        },
                    ],
                }
            }
        )

        results = client.search_movies("office space", limit=2)

        self.assertEqual([item.tmdb_id for item in results], [11, 12])

    def test_search_can_bias_to_primary_release_year(self) -> None:
        client = TmdbClient("plain-v3-key", timeout_seconds=15)
        fake_http = _FakeHttp(
            {
                1: {
                    "total_pages": 1,
                    "results": [
                        {
                            "id": 21,
                            "title": "Batman",
                            "release_date": "1989-06-23",
                            "overview": "",
                            "original_language": "en",
                            "poster_path": None,
                            "genre_ids": [28],
                            "popularity": 20,
                            "vote_count": 10,
                            "video": False,
                        }
                    ],
                }
            }
        )
        client.http = fake_http

        results = client.search_movies("batman", limit=5, primary_release_year=1989)

        self.assertEqual([item.tmdb_id for item in results], [21])
        self.assertEqual(fake_http.params[0]["primary_release_year"], "1989")


if __name__ == "__main__":
    unittest.main()
