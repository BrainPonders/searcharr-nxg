"""Tests for Telegram bot helpers."""

from __future__ import annotations

import unittest

from searcharr_nxg.domain.decision_model import Action
from searcharr_nxg.integrations.radarr import RadarrOption
from searcharr_nxg.integrations.tmdb import TmdbMovieCandidate
from searcharr_nxg.services.movie_inspection import build_movie_inspection_report
from searcharr_nxg.telegram_bot import (
    action_button_rows,
    browser_button_rows,
    exclusion_button_rows,
    profile_button_rows,
)


class TelegramBotHelperTests(unittest.TestCase):
    def test_browser_keyboard_uses_navigation_and_select(self) -> None:
        rows = browser_button_rows(
            TmdbMovieCandidate(
                tmdb_id=558,
                title="Spider-Man 2",
                release_date="2004-06-25",
                overview="",
                original_language="en",
                poster_path=None,
            )
        )

        self.assertEqual(rows[0][0]["text"], "<")
        self.assertEqual(rows[0][0]["callback_data"], "browse:-1")
        self.assertEqual(rows[0][1]["text"], "TMDB")
        self.assertEqual(rows[0][1]["url"], "https://www.themoviedb.org/movie/558")
        self.assertEqual(rows[0][2]["text"], ">")
        self.assertEqual(rows[0][2]["callback_data"], "browse:1")
        self.assertEqual(rows[1][0]["text"], "Select")
        self.assertEqual(rows[1][0]["callback_data"], "select")
        self.assertEqual(rows[1][1]["text"], "Cancel")
        self.assertEqual(rows[1][1]["callback_data"], "cancel:search")

    def test_action_keyboard_uses_human_labels(self) -> None:
        report = build_movie_inspection_report(
            TmdbMovieCandidate(
                tmdb_id=10,
                title="Example",
                release_date=None,
                overview="",
                original_language=None,
                poster_path=None,
            )
        )

        rows = action_button_rows(report)

        self.assertEqual(rows[0][0]["text"], "Add Movie")
        self.assertEqual(rows[0][0]["callback_data"], "act:10:add_movie")
        self.assertEqual(rows[0][1]["text"], "Add + Search")
        self.assertEqual(rows[0][1]["callback_data"], "act:10:add_and_search")
        self.assertEqual(rows[-1][0]["text"], "Cancel")
        self.assertEqual(rows[-1][0]["callback_data"], "cancel:action")

    def test_profile_keyboard_uses_profile_ids(self) -> None:
        rows = profile_button_rows(
            10,
            Action.ADD_MOVIE,
            [
                RadarrOption(id=7, name="Movies > 4K EN+FR", raw={}),
                RadarrOption(id=8, name="Movies > HD", raw={}),
            ],
        )

        self.assertEqual(rows[0][0]["text"], "Movies > 4K EN+FR")
        self.assertEqual(rows[0][0]["callback_data"], "profile:10:add_movie:7")
        self.assertEqual(rows[1][0]["callback_data"], "profile:10:add_movie:8")
        self.assertEqual(rows[-1][0]["callback_data"], "cancel:action")

    def test_exclusion_keyboard_requires_continue_or_cancel(self) -> None:
        rows = exclusion_button_rows(10, Action.ADD_MOVIE)

        self.assertEqual(rows[0][0]["text"], "Add Movie Anyway")
        self.assertEqual(rows[0][0]["callback_data"], "continue:10:add_movie")
        self.assertEqual(rows[1][0]["text"], "Cancel")
        self.assertEqual(rows[1][0]["callback_data"], "cancel:action")


if __name__ == "__main__":
    unittest.main()
