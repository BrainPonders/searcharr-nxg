# Reference Survey

Survey of the upstream Searcharr lineage used to shape Searcharr-nxg.

## History

- `2026-03-23 | Codex | Compared BrainPonders/searcharr-ngx and ishan190425/searcharr during the workspace reset`

## Scope & Boundaries

- This document records which upstream repositories were inspected and how they should influence Searcharr-nxg.
- It is not a compatibility promise.
- It should be updated when a new upstream source becomes relevant to the project.

## Authority (Owned Facts)

This document owns:

- the current reference-repository list
- the observed reuse boundaries
- the reasons those repositories are not the direct structural base for this workspace

## Authoritative Inputs (Consumed Facts)

This document consumes:

- local clones of `BrainPonders/searcharr-ngx`
- local clones of `ishan190425/searcharr`
- the Searcharr-nxg product handover and design specification

## Change Rules

- Keep this document focused on observed engineering facts.
- Prefer concise conclusions over file-by-file inventories.
- Update it when a reference repository materially changes Searcharr-nxg direction.

## Repositories Reviewed

### `BrainPonders/searcharr-ngx`

Observed characteristics:

- flat Python script repository
- direct `settings.py` import model
- Telegram bot flow implemented in a single main script
- Radarr, Sonarr, and Readarr wrappers split into separate modules
- language resources under `lang/`
- Docker and GitHub workflow assets present

Useful inputs:

- Telegram interaction patterns
- Arr API wrapper patterns
- upstream language resources retained in this workspace
- configuration vocabulary already familiar to Searcharr users

Reasons it is not the structural base for Searcharr-nxg:

- no maintainer/documentation template
- legacy flat layout instead of the chosen `src` package layout
- no Ryot-centric decision layer
- local sqlite state and direct add-to-Arr flow do not match the new architecture

### `ishan190425/searcharr`

Observed characteristics:

- inherits the same flat script foundation
- adds experimental patches such as Docker container monitoring and queue-status commands
- moves Telegram bot usage toward the newer `Application` API

Useful inputs:

- selective patch mining for side features
- examples of post-fork customizations that may still be relevant later

Reasons it is not the structural base for Searcharr-nxg:

- still built on the legacy Searcharr shape
- feature additions are sidecars, not architectural improvements
- does not address the Ryot-first decision model

## Current Reuse Strategy

- keep `lang/` resources from the Searcharr lineage
- mine upstream wrappers and Telegram flows selectively when implementation begins
- do not inherit the upstream repository layout wholesale
- treat Readarr support as out of current scope unless the product direction expands again
