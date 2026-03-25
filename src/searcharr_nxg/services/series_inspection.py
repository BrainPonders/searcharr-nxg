"""Series inspection flow for Searcharr-nxg."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from searcharr_nxg.domain.decision_model import Action, RyotState, SonarrState, actions_for_sonarr_state, watched_warning
from searcharr_nxg.integrations.ryot import RyotSeriesRecord
from searcharr_nxg.integrations.sonarr import SonarrSeriesRecord
from searcharr_nxg.integrations.tmdb import TmdbSeriesCandidate


@dataclass(frozen=True)
class SeriesInspectionReport:
    """Combined summary for one series candidate."""

    candidate: TmdbSeriesCandidate
    ryot: RyotSeriesRecord
    sonarr: SonarrSeriesRecord
    warning: Optional[str]
    actions: Sequence[Action]


def build_series_inspection_report(
    candidate: TmdbSeriesCandidate,
    *,
    ryot: Optional[RyotSeriesRecord] = None,
    sonarr: Optional[SonarrSeriesRecord] = None,
) -> SeriesInspectionReport:
    """Build a compact series report from Ryot and Sonarr records."""

    ryot_record = ryot or RyotSeriesRecord(
        state=RyotState.NOT_IN_RYOT,
        metadata_id=None,
        title=None,
        identifier=None,
        seen_by_user_count=0,
        last_finished_on=None,
        has_interacted=False,
        collection_names=[],
    )
    sonarr_record = sonarr or SonarrSeriesRecord(
        state=SonarrState.NOT_IN_SONARR,
        title=None,
        monitored=False,
        has_files=False,
        quality_profile_id=None,
        quality_profile_name=None,
        folder_path=None,
        tags=[],
        size_bytes=None,
        episode_file_count=0,
        episode_count=0,
        is_excluded=False,
    )

    return SeriesInspectionReport(
        candidate=candidate,
        ryot=ryot_record,
        sonarr=sonarr_record,
        warning=watched_warning(ryot_record.state).replace("movie", "series")
        if watched_warning(ryot_record.state)
        else None,
        actions=actions_for_sonarr_state(sonarr_record.state),
    )
