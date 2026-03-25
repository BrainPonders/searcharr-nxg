"""Tests for render helpers."""

from __future__ import annotations

import unittest

from searcharr_nxg.domain.decision_model import Action
from searcharr_nxg.integrations.tmdb import TmdbMovieCandidate
from searcharr_nxg.render import (
    action_label,
    render_candidate_browser_message,
    render_movie_action_preview,
    render_movie_inspection_message,
)
from searcharr_nxg.domain.decision_model import RadarrState, RyotState
from searcharr_nxg.integrations.radarr import RadarrMovieRecord
from searcharr_nxg.integrations.ryot import RyotMovieRecord
from searcharr_nxg.services.movie_actions import MovieActionPreview
from searcharr_nxg.services.movie_inspection import build_movie_inspection_report


class RenderTests(unittest.TestCase):
    def test_action_label_is_human_readable(self) -> None:
        self.assertEqual(action_label(Action.ADD_AND_SEARCH), "Add + Search")

    def test_executed_movie_update_is_summarized(self) -> None:
        preview = MovieActionPreview(
            action=Action.UNMONITOR,
            execute=True,
            allowed=True,
            message="Radarr monitored state updated.",
            details={
                "id": 2999,
                "title": "Spider-Man 2",
                "tmdbId": 558,
                "monitored": False,
                "qualityProfileId": 16,
                "rootFolderPath": "/data/movies",
                "movieFile": {
                    "quality": {
                        "quality": {
                            "name": "Remux-2160p",
                        }
                    }
                },
                "alternateTitles": [{"title": "Spider-Man II"}],
            },
        )

        rendered = render_movie_action_preview(preview)

        self.assertIn("- movie_id: 2999", rendered)
        self.assertIn("- title: Spider-Man 2", rendered)
        self.assertIn("- current_quality: Remux-2160p", rendered)
        self.assertNotIn("alternateTitles", rendered)

    def test_tmdb_candidate_builds_poster_url(self) -> None:
        candidate = TmdbMovieCandidate(
            tmdb_id=558,
            title="Spider-Man 2",
            release_date="2004-06-25",
            overview="",
            original_language="en",
            poster_path="/eg8XHjA7jkM3ulBLnfGTczR9ytI.jpg",
        )

        self.assertEqual(
            candidate.poster_url,
            "https://image.tmdb.org/t/p/w500/eg8XHjA7jkM3ulBLnfGTczR9ytI.jpg",
        )

    def test_candidate_browser_message_is_compact(self) -> None:
        candidate = TmdbMovieCandidate(
            tmdb_id=558,
            title="Spider-Man 2",
            release_date="2004-06-25",
            overview="Peter Parker is going through a major identity crisis.",
            original_language="en",
            poster_path="/eg8XHjA7jkM3ulBLnfGTczR9ytI.jpg",
        )

        rendered = render_candidate_browser_message(candidate, 1, 5)

        self.assertIn("Spider-Man 2 (2004)", rendered)
        self.assertIn("1/5", rendered)
        self.assertIn("identity crisis", rendered)

    def test_movie_inspection_message_focuses_on_orion_stack(self) -> None:
        candidate = TmdbMovieCandidate(
            tmdb_id=102382,
            title="The Amazing Spider-Man 2",
            release_date="2014-04-16",
            overview="",
            original_language="en",
            poster_path="/x.jpg",
        )
        ryot = RyotMovieRecord(
            state=RyotState.IN_RYOT_WATCHED,
            metadata_id="meta-1",
            title="The Amazing Spider-Man 2",
            identifier="102382",
            seen_by_user_count=2,
            last_finished_on="2016-06-20T19:44:00+00:00",
            has_interacted=True,
            collection_names=["Watchlist", "Owned", "Completed"],
        )
        radarr = RadarrMovieRecord(
            state=RadarrState.MONITORED_MISSING,
            title="The Amazing Spider-Man 2",
            monitored=True,
            has_file=False,
            quality_profile_id=16,
            quality_profile_name="Movies > 4K EN+FR",
            minimum_availability="released",
            folder_path="/data/movies",
            tags=[],
            raw_quality=None,
            size_bytes=None,
            previously_owned=False,
            is_excluded=False,
        )

        rendered = render_movie_inspection_message(
            build_movie_inspection_report(candidate, ryot=ryot, radarr=radarr)
        )

        self.assertIn("<b>Ryot:</b> <code>Registered</code>", rendered)
        self.assertIn("<b>Watched:</b> <code>2x | 20-Jun-2016 @ 19:44</code>", rendered)
        self.assertIn("<b>Collections:</b> <code>Watchlist | Owned | Completed</code>", rendered)
        self.assertIn("<b>Radarr:</b> <code>Monitored</code>", rendered)
        self.assertIn("<b>Quality Profile:</b> <code>Movies &gt; 4K EN+FR</code>", rendered)
        self.assertIn("<b>Available:</b> <code>Missing</code>", rendered)
        self.assertNotIn("<b>Excluded:</b>", rendered)


if __name__ == "__main__":
    unittest.main()
