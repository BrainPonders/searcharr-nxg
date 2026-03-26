# System Architecture

Tracked architecture and decision-model reference for Searcharr-nxg.

## History

- `2026-03-23 | Codex | Initialized the tracked architecture baseline from the project handover and design specification`
- `2026-03-26 | Codex | Recorded Ryot-Arr state-sync brainstorm, ownership model concerns, and proposed bridge direction`

## Scope & Boundaries

- This document defines the current product model for Searcharr-nxg.
- It covers user-facing flow, service boundaries, decision states, and MVP implementation phases.
- It does not define maintainer workflow or release process; those live under `maintainer/`.

## Authority (Owned Facts)

This document owns:

- the current component-role model
- the request decision flow
- the Ryot and Radarr state model
- the allowed action mapping for the movie-first MVP

## Authoritative Inputs (Consumed Facts)

This document consumes:

- the project handover provided for Searcharr-nxg
- the design specification kept under `.local/handover/`
- observed behavior and structure from the upstream Searcharr lineage

## Change Rules

- Keep this document aligned to the real implementation target, not to inherited legacy behavior.
- Favor explicit component roles over vague platform descriptions.
- When the runtime behavior changes materially, update this document in the same change set.

## Objective

Searcharr-nxg is a Telegram-based request system that evaluates each action against:

- user history in Ryot
- current movie state in Radarr
- metadata search results from TMDB

The product goal is to prevent unnecessary downloads, warn about previously watched media, and offer controlled actions instead of blindly adding titles.

## Component Roles

- `Ryot`
  - long-term memory
  - source of truth for watched history
  - persistent state that survives storage rebuilds
- `Radarr`
  - movie acquisition and storage execution layer
  - cache of what currently exists or is tracked
  - not the primary decision source
- `Sonarr`
  - planned future equivalent of the Radarr integration for series
- `TMDB`
  - search and candidate metadata provider
- `Telegram`
  - user interface and control surface
- `Jellyfin`
  - passive playback sensor that feeds Ryot through existing webhook flow

## Request Flow

1. A user sends a movie command such as `/movie Spider-Man 2`.
2. Searcharr-nxg queries TMDB and returns candidate results.
3. The user selects a movie candidate.
4. Searcharr-nxg enters decision mode and queries:
   - Ryot for existence, watched status, last watched timestamp, and watch count
   - Radarr for presence, monitored state, file presence, profile, quality, size, and tags
5. Searcharr-nxg renders a summary and the allowed action buttons.
6. The selected action is then executed against Radarr.

## State Model

### Ryot State

| Code | Meaning |
| --- | --- |
| `R0` | Not in Ryot |
| `R1` | In Ryot, not watched |
| `R2` | In Ryot, watched |

### Radarr State

| Code | Meaning |
| --- | --- |
| `A0` | Not in Radarr |
| `A1` | Exists, monitored, no file |
| `A2` | Exists, unmonitored, no file |
| `A3` | Exists, monitored, file present |
| `A4` | Exists, unmonitored, file present |

### Modifiers

Modifiers are not states. They enrich the decision context.

- `previously_owned`
- `quality_meets_profile`
- `current_quality`
- `current_size`
- `desired_profile`

## Derived Logic

- `previously_owned = true`
  - when a Radarr entry exists, the file is missing, and the title was previously downloaded
  - the current preferred mechanism is a Radarr tag named `previously_owned`
- `quality_meets_profile = true`
  - when the current file quality satisfies the desired profile

## Critical UX Rule

If Ryot state is `R2`, Searcharr-nxg must always display a warning equivalent to:

`You already watched this movie`

This warning is independent of the current Radarr state.

## Allowed Actions

| Radarr state | Allowed actions |
| --- | --- |
| `A0` | Add Movie, Add + Search |
| `A1` | Search Now, Change Profile, Unmonitor |
| `A2` | Re-monitor, Search Now, Change Profile |
| `A3` | Open in Jellyfin, Search Upgrade, Change Profile, Unmonitor |
| `A4` | Open in Jellyfin, Re-monitor, Change Profile |

## Integration Rules

### Radarr

- Prefer edit and monitor-state changes over delete-and-readd flows.
- Do not delete movies automatically.
- Respect the Radarr exclusion list and surface that condition explicitly.
- MVP actions should rely on:
  - lookup by TMDB or IMDb
  - add movie
  - edit monitored state
  - trigger search

### Ryot

- MVP requires read access for:
  - lookup by TMDB or IMDb
  - watched state
  - last watched
  - history
- Writing back into Ryot is future scope.

## Future State Sync Brainstorm

This section records the current design direction for Ryot and Arr consistency work. It is not yet implemented end to end, but it captures the intended architecture so work can resume later without repeating the discussion.

### Problem Statement

- Deleting titles from Radarr to keep the database lean loses useful history.
- `Unmonitored` alone is not enough to explain what happened to a title.
- A movie may have been:
  - added but never downloaded
  - downloaded and never watched
  - watched and later deleted from storage
- Searcharr-nxg should preserve enough context to help avoid unnecessary re-downloads and to make Radarr and Ryot reflect the same user intent.

### Directional Conclusion

- Prefer keeping titles in Radarr and Sonarr instead of deleting them in normal cleanup flows.
- Use monitored state only for current acquisition intent.
- Use Ryot as the long-term historical memory for user state.
- Treat history and acquisition state as different concerns.

### Vocabulary Direction

- `owned`
  - means the title has been part of the local library before
  - preferred over `downloaded` because it matches Ryot language better
- `watched`
  - means the title has been consumed before
- `unmonitored`
  - must remain an operational state only
  - it must not be treated as proof that something was owned or watched

### Partial Conclusions

- Ryot already receives watched status from Jellyfin, so watched history is not the missing source-of-truth problem.
- The harder missing signal is how to populate `Owned` in Ryot automatically.
- Radarr and Sonarr still benefit from visible tags such as `watched`, even if Ryot remains the authoritative historical source.
- A future `previously_owned` concept is currently less attractive than standardizing around `Owned`.

### Proposed Authority Split

- `Ryot`
  - authoritative for `Watched`
  - intended future authority for `Owned`
- `Radarr` and `Sonarr`
  - authoritative for current monitored state, current file presence, current profile, and execution actions
  - consumers of mirrored historical tags where useful for operator visibility
- `Searcharr-nxg`
  - optional bridge and policy engine between Ryot and Arr
  - responsible for translating signals, applying rules, and avoiding split-brain behavior

### Proposed Bridge Flows

#### Arr to Ryot

- Radarr and Sonarr can send webhooks to Searcharr-nxg when media is imported.
- Searcharr-nxg can use those import events to update the `Owned` collection in Ryot.
- This is the strongest current candidate for making `Owned` automatic.

#### Ryot to Arr

- Jellyfin already feeds watched state into Ryot.
- Searcharr-nxg can read watched state from Ryot and mirror a `watched` tag into Radarr and Sonarr.
- Ryot does not necessarily need to push events directly if Searcharr-nxg can poll or reconcile watched state on demand.

### Open Questions

- Which webhook payload fields from Radarr and Sonarr are reliable enough to resolve a Ryot item without ambiguity.
- Whether Ryot exposes the exact collection-write operations needed for robust `Owned` synchronization in all required cases.
- Whether watched-tag mirroring should be:
  - scheduled polling
  - on-demand reconciliation during Searcharr actions
  - or a hybrid model
- Whether `owned` also needs to be mirrored back into Arr as a visible tag, or whether Ryot-only ownership is sufficient.

### Constraints and Risks

- `Owned` is not currently known to be automatically maintained by Ryot for physical/local library titles.
- `Watched` is easier to automate than `Owned`.
- Matching media reliably across TMDB, TVDB, IMDb, Ryot, Radarr, and Sonarr remains an architectural risk.
- Searcharr-nxg should avoid making Arr and Ryot both authoritative for the same historical fact.

### Implementation Status

- not implemented yet
- intended to be optional and configurable when introduced
- should be resumed only after the current release/runtime path is stable again

## MVP Phases

### Phase 1

- TMDB search flow
- Ryot lookup
- Radarr lookup
- decision summary message
- action buttons

### Phase 2

- previously-owned tagging
- profile changes
- upgrade detection

### Phase 3

- Sonarr support
- Jellyfin deep links
- history insights

## Known Edge Cases

- movie exists in Radarr but is excluded from re-add
- movie was watched in Ryot but does not exist in Radarr
- movie exists in multiple qualities or has profile mismatches
- TMDB and IMDb identifiers disagree or match incorrectly
