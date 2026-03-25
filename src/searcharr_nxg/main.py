"""CLI bootstrap for Searcharr-nxg."""

from __future__ import annotations

import argparse
import logging

from searcharr_nxg import __version__
from searcharr_nxg.config import integration_summary, load_settings
from searcharr_nxg.domain.decision_model import Action
from searcharr_nxg.http import IntegrationError
from searcharr_nxg.logging_utils import configure_logging
from searcharr_nxg.render import render_movie_action_preview, render_movie_inspection, render_series_inspection
from searcharr_nxg.runtime import SearcharrRuntime
from searcharr_nxg.telegram_bot import run_telegram_bot


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="searcharr-nxg",
        description="Bootstrap the Searcharr-nxg service scaffold.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging.",
    )
    parser.add_argument(
        "--settings-file",
        help="Explicit path to settings.py. Defaults to SEARCHARR_SETTINGS_FILE, ./settings.py, or the repository root settings.py.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Load configuration and exit without entering the long-running scaffold loop.",
    )
    parser.add_argument(
        "--inspect-movie",
        help="Inspect a movie decision by searching TMDB with the provided title.",
    )
    parser.add_argument(
        "--inspect-series",
        help="Inspect a series decision by searching TMDB TV with the provided title.",
    )
    parser.add_argument(
        "--tmdb-id",
        type=int,
        help="Inspect a movie or series decision using a specific TMDB id.",
    )
    parser.add_argument(
        "--candidate-index",
        type=int,
        default=1,
        help="1-based result index to use with --inspect-movie. Defaults to 1.",
    )
    parser.add_argument(
        "--perform-action",
        choices=[action.value for action in Action],
        help="Preview or execute a movie action after inspection.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually send write requests for --perform-action. Without this flag, only a preview is shown.",
    )
    parser.add_argument(
        "--quality-profile",
        help="Quality profile id or name to use for add/change-profile actions.",
    )
    parser.add_argument(
        "--root-folder",
        help="Root folder id or path to use for add actions.",
    )
    parser.add_argument(
        "--telegram-bot",
        action="store_true",
        help="Start the Telegram bot polling runtime.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def inspect_movie(args: argparse.Namespace, runtime: SearcharrRuntime) -> str:
    """Inspect a movie through TMDB, Ryot, and Radarr."""

    if args.tmdb_id:
        report = runtime.inspect_tmdb_movie(args.tmdb_id)
    else:
        report = runtime.inspect_movie_query(
            args.inspect_movie or "",
            candidate_index=args.candidate_index,
        )
    if args.perform_action:
        action_preview = runtime.perform_movie_action(
            tmdb_id=report.candidate.tmdb_id,
            action=Action(args.perform_action),
            execute=args.execute,
            quality_profile=args.quality_profile,
            root_folder=args.root_folder,
        )
        return render_movie_action_preview(action_preview)
    return render_movie_inspection(report)


def inspect_series(args: argparse.Namespace, runtime: SearcharrRuntime) -> str:
    """Inspect a series through TMDB and Sonarr."""

    if args.tmdb_id:
        report = runtime.inspect_tmdb_series(args.tmdb_id)
    else:
        report = runtime.inspect_series_query(
            args.inspect_series or "",
            candidate_index=args.candidate_index,
        )
    return render_series_inspection(report)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    configure_logging(verbose=args.verbose)
    logger = logging.getLogger("searcharr_nxg")

    try:
        loaded_settings = load_settings(args.settings_file)
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2
    logger.info("Searcharr-nxg bootstrap starting")
    logger.info("Loaded settings from %s", loaded_settings.path)

    for name, enabled in integration_summary(loaded_settings.module).items():
        logger.info("Integration %-8s enabled=%s", name, enabled)

    if args.dry_run:
        logger.info("Dry run completed successfully.")
        return 0

    try:
        runtime = SearcharrRuntime.from_settings(loaded_settings.module)
        if args.inspect_series:
            print(inspect_series(args, runtime))
            return 0
        if args.inspect_movie or args.tmdb_id:
            print(inspect_movie(args, runtime))
            return 0
        if args.telegram_bot or getattr(loaded_settings.module, "tgram_token", ""):
            run_telegram_bot(runtime, logger)
            return 0
    except (IntegrationError, RuntimeError) as exc:
        logger.error("%s", exc)
        return 2

    logger.error("No runnable mode selected. Configure tgram_token or pass an inspection command.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
