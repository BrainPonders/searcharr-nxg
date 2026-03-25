"""Decision-model primitives derived from the Searcharr-nxg handover."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple


class RyotState(str, Enum):
    """Ryot-backed user history states."""

    NOT_IN_RYOT = "R0"
    IN_RYOT_NOT_WATCHED = "R1"
    IN_RYOT_WATCHED = "R2"


class RadarrState(str, Enum):
    """Current Radarr presence and file states."""

    NOT_IN_RADARR = "A0"
    MONITORED_MISSING = "A1"
    UNMONITORED_MISSING = "A2"
    MONITORED_PRESENT = "A3"
    UNMONITORED_PRESENT = "A4"


class Action(str, Enum):
    """User actions currently defined by the product design."""

    ADD_MOVIE = "add_movie"
    ADD_AND_SEARCH = "add_and_search"
    SEARCH_NOW = "search_now"
    CHANGE_PROFILE = "change_profile"
    UNMONITOR = "unmonitor"
    REMONITOR = "remonitor"
    OPEN_IN_JELLYFIN = "open_in_jellyfin"
    SEARCH_UPGRADE = "search_upgrade"


@dataclass(frozen=True)
class DecisionModifiers:
    """Non-state flags and values that enrich the decision context."""

    previously_owned: bool = False
    quality_meets_profile: Optional[bool] = None
    current_quality: Optional[str] = None
    current_size: Optional[int] = None
    desired_profile: Optional[str] = None


@dataclass(frozen=True)
class DecisionContext:
    """Minimal product-level decision context for a movie."""

    ryot_state: RyotState
    radarr_state: RadarrState
    modifiers: DecisionModifiers = DecisionModifiers()


def actions_for_state(radarr_state: RadarrState) -> Tuple[Action, ...]:
    """Return the allowed actions for the given Radarr state."""

    mapping = {
        RadarrState.NOT_IN_RADARR: (
            Action.ADD_MOVIE,
            Action.ADD_AND_SEARCH,
        ),
        RadarrState.MONITORED_MISSING: (
            Action.SEARCH_NOW,
            Action.CHANGE_PROFILE,
            Action.UNMONITOR,
        ),
        RadarrState.UNMONITORED_MISSING: (
            Action.REMONITOR,
            Action.SEARCH_NOW,
            Action.CHANGE_PROFILE,
        ),
        RadarrState.MONITORED_PRESENT: (
            Action.OPEN_IN_JELLYFIN,
            Action.SEARCH_UPGRADE,
            Action.CHANGE_PROFILE,
            Action.UNMONITOR,
        ),
        RadarrState.UNMONITORED_PRESENT: (
            Action.OPEN_IN_JELLYFIN,
            Action.REMONITOR,
            Action.CHANGE_PROFILE,
        ),
    }
    return mapping[radarr_state]


def watched_warning(ryot_state: RyotState) -> Optional[str]:
    """Return the mandatory watched warning when Ryot indicates history."""

    if ryot_state is RyotState.IN_RYOT_WATCHED:
        return "You already watched this movie"
    return None
