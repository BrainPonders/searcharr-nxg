"""Tests for the Sonarr client scaffold."""

from __future__ import annotations

import unittest

from searcharr_nxg.integrations.sonarr import SonarrClient, SonarrOption


class SonarrClientTests(unittest.TestCase):
    def test_match_option_resolves_by_id_or_name(self) -> None:
        options = [
            SonarrOption(id=7, name="Shows > 4K EN+FR", raw={}),
            SonarrOption(id=8, name="Shows - 1080p EN+FR", raw={}),
        ]

        self.assertEqual(SonarrClient._match_option(options, 7), options[0])
        self.assertEqual(SonarrClient._match_option(options, "Shows - 1080p EN+FR"), options[1])
        self.assertIsNone(SonarrClient._match_option(options, "missing"))


if __name__ == "__main__":
    unittest.main()
