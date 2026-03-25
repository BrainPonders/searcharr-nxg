"""Tests for movie action previews."""

from __future__ import annotations

import unittest

from searcharr_nxg.domain.decision_model import Action, RadarrState, RyotState
from searcharr_nxg.integrations.radarr import RadarrActionResponse, RadarrMovieRecord, RadarrOption
from searcharr_nxg.integrations.ryot import RyotMovieRecord
from searcharr_nxg.integrations.tmdb import TmdbMovieCandidate
from searcharr_nxg.services.movie_actions import preview_or_execute_movie_action
from searcharr_nxg.services.movie_inspection import build_movie_inspection_report


class _Settings:
    radarr_quality_profile_id = ["Movies > 4K EN+FR"]
    radarr_movie_paths = ["/movies"]
    radarr_forced_tags = []
    radarr_min_availability = "released"
    radarr_add_monitored = True
    jellyfin_base_url = "https://jellyfin.example"


class _FakeRadarrClient:
    def resolve_quality_profile(self, value):
        return RadarrOption(id=7, name="Movies > 4K EN+FR", raw={})

    def resolve_root_folder(self, value):
        return RadarrOption(id=2, name="/movies", raw={})

    def resolve_tag(self, value):
        return RadarrOption(id=9, name=str(value), raw={})

    def list_root_folders(self):
        return [RadarrOption(id=2, name="/movies", raw={})]

    def _find_movie_by_tmdb_id(self, tmdb_id):
        return {"id": 123, "tmdbId": tmdb_id}

    def add_movie(self, **kwargs):
        return RadarrActionResponse("add_movie", 123, True, kwargs)

    def update_movie(self, movie_id, **kwargs):
        return RadarrActionResponse("update_movie", movie_id, True, kwargs)

    def search_movie(self, movie_id):
        return RadarrActionResponse("search_movie", movie_id, True, {"movieIds": [movie_id]})


def _candidate():
    return TmdbMovieCandidate(
        tmdb_id=558,
        title="Spider-Man 2",
        release_date="2004-06-25",
        overview="",
        original_language="en",
        poster_path=None,
    )


def _ryot():
    return RyotMovieRecord(
        state=RyotState.IN_RYOT_NOT_WATCHED,
        metadata_id="abc",
        title="Spider-Man 2",
        identifier="558",
        seen_by_user_count=0,
        last_finished_on=None,
        has_interacted=True,
        collection_names=["Watchlist"],
    )


class MovieActionTests(unittest.TestCase):
    def test_add_movie_preview_uses_configured_defaults(self) -> None:
        report = build_movie_inspection_report(_candidate(), ryot=_ryot())
        preview = preview_or_execute_movie_action(
            action=Action.ADD_MOVIE,
            report=report,
            radarr_client=_FakeRadarrClient(),
            settings_module=_Settings,
            execute=False,
        )
        self.assertTrue(preview.allowed)
        self.assertFalse(preview.execute)
        self.assertEqual(preview.details["quality_profile_id"], 7)
        self.assertEqual(preview.details["root_folder_path"], "/movies")

    def test_unmonitor_executes_for_present_movie(self) -> None:
        radarr = RadarrMovieRecord(
            state=RadarrState.MONITORED_PRESENT,
            title="Spider-Man 2",
            monitored=True,
            has_file=True,
            quality_profile_id=7,
            quality_profile_name="Movies > 4K EN+FR",
            minimum_availability="released",
            folder_path="/movies/Spider-Man 2",
            tags=[],
            raw_quality="Remux-2160p",
            size_bytes=1,
            previously_owned=False,
            is_excluded=False,
        )
        report = build_movie_inspection_report(_candidate(), ryot=_ryot(), radarr=radarr)
        preview = preview_or_execute_movie_action(
            action=Action.UNMONITOR,
            report=report,
            radarr_client=_FakeRadarrClient(),
            settings_module=_Settings,
            execute=True,
        )
        self.assertTrue(preview.allowed)
        self.assertTrue(preview.execute)
        self.assertEqual(preview.message, "Radarr monitored state updated.")

    def test_disallowed_action_is_blocked(self) -> None:
        report = build_movie_inspection_report(_candidate(), ryot=_ryot())
        preview = preview_or_execute_movie_action(
            action=Action.UNMONITOR,
            report=report,
            radarr_client=_FakeRadarrClient(),
            settings_module=_Settings,
            execute=False,
        )
        self.assertFalse(preview.allowed)


if __name__ == "__main__":
    unittest.main()
