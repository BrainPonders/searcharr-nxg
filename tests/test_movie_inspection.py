"""Tests for the movie inspection service."""

from __future__ import annotations

import unittest

from searcharr_nxg.domain.decision_model import Action, RadarrState, RyotState
from searcharr_nxg.integrations.radarr import RadarrMovieRecord
from searcharr_nxg.integrations.ryot import RyotMovieRecord
from searcharr_nxg.integrations.tmdb import TmdbMovieCandidate
from searcharr_nxg.render import render_movie_inspection
from searcharr_nxg.services.movie_inspection import build_movie_inspection_report


class MovieInspectionTests(unittest.TestCase):
    def test_watched_movie_in_radarr_present_state(self) -> None:
        candidate = TmdbMovieCandidate(
            tmdb_id=558,
            title="Spider-Man 2",
            release_date="2004-06-25",
            overview="",
            original_language="en",
            poster_path=None,
        )
        ryot = RyotMovieRecord(
            state=RyotState.IN_RYOT_WATCHED,
            metadata_id="meta-1",
            title="Spider-Man 2",
            identifier="558",
            seen_by_user_count=1,
            last_finished_on="2025-03-23T10:00:00Z",
            has_interacted=True,
            collection_names=["Owned", "Completed"],
        )
        radarr = RadarrMovieRecord(
            state=RadarrState.UNMONITORED_MISSING,
            title="Spider-Man 2",
            monitored=False,
            has_file=False,
            quality_profile_id=7,
            quality_profile_name="Remux-2160p",
            minimum_availability="released",
            folder_path="/movies/Spider-Man 2",
            tags=[1],
            raw_quality=None,
            size_bytes=None,
            previously_owned=True,
            is_excluded=False,
        )

        report = build_movie_inspection_report(candidate, ryot=ryot, radarr=radarr)

        self.assertEqual(report.warning, "You already watched this movie")
        self.assertEqual(report.actions, (Action.REMONITOR, Action.SEARCH_NOW, Action.CHANGE_PROFILE))
        self.assertTrue(report.context.modifiers.previously_owned)

    def test_renderer_includes_warning_and_actions(self) -> None:
        candidate = TmdbMovieCandidate(
            tmdb_id=10,
            title="Example",
            release_date=None,
            overview="",
            original_language=None,
            poster_path=None,
        )
        report = build_movie_inspection_report(candidate)
        rendered = render_movie_inspection(report)
        self.assertIn("Actions", rendered)
        self.assertIn("add_movie", rendered)
        self.assertIn("add_and_search", rendered)


if __name__ == "__main__":
    unittest.main()
