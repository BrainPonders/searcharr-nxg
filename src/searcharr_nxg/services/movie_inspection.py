"""Movie inspection flow for Searcharr-nxg."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from searcharr_nxg.domain.decision_model import (
    Action,
    DecisionContext,
    DecisionModifiers,
    RadarrState,
    RyotState,
    actions_for_state,
    watched_warning,
)
from searcharr_nxg.integrations.radarr import RadarrMovieRecord
from searcharr_nxg.integrations.ryot import RyotMovieRecord
from searcharr_nxg.integrations.tmdb import TmdbMovieCandidate


@dataclass(frozen=True)
class MovieInspectionReport:
    """Combined decision summary for one movie candidate."""

    candidate: TmdbMovieCandidate
    ryot: RyotMovieRecord
    radarr: RadarrMovieRecord
    context: DecisionContext
    warning: Optional[str]
    actions: Sequence[Action]


def build_movie_inspection_report(
    candidate: TmdbMovieCandidate,
    *,
    ryot: Optional[RyotMovieRecord] = None,
    radarr: Optional[RadarrMovieRecord] = None,
) -> MovieInspectionReport:
    """Build a decision report from the available upstream records."""

    ryot_record = ryot or RyotMovieRecord(
        state=RyotState.NOT_IN_RYOT,
        metadata_id=None,
        title=None,
        identifier=None,
        seen_by_user_count=0,
        last_finished_on=None,
        has_interacted=False,
        collection_names=[],
    )
    radarr_record = radarr or RadarrMovieRecord(
        state=RadarrState.NOT_IN_RADARR,
        title=None,
        monitored=False,
        has_file=False,
        quality_profile_id=None,
        quality_profile_name=None,
        minimum_availability=None,
        folder_path=None,
        tags=[],
        raw_quality=None,
        size_bytes=None,
        previously_owned=False,
        is_excluded=False,
    )

    modifiers = DecisionModifiers(
        previously_owned=radarr_record.previously_owned,
        quality_meets_profile=None,
        current_quality=radarr_record.raw_quality,
        current_size=radarr_record.size_bytes,
        desired_profile=radarr_record.quality_profile_name,
    )
    context = DecisionContext(
        ryot_state=ryot_record.state,
        radarr_state=radarr_record.state,
        modifiers=modifiers,
    )
    return MovieInspectionReport(
        candidate=candidate,
        ryot=ryot_record,
        radarr=radarr_record,
        context=context,
        warning=watched_warning(ryot_record.state),
        actions=actions_for_state(radarr_record.state),
    )
