"""Logging helpers for Searcharr-nxg."""

from __future__ import annotations

import logging
import sys


def configure_logging(verbose: bool = False) -> None:
    """Configure root logging for CLI and container usage."""

    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        stream=sys.stdout,
    )
