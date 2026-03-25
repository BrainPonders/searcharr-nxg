# Documentation Governance Principles

Tracked rules for documentation ownership, structure, and runtime header usage.

## History

- `2026-03-10 | Codex | Initial tracked documentation-governance principles for the project template`
- `2026-03-23 | Codex | Adapted the template governance model for Searcharr-nxg`

<br>

## Table of Contents

- [Purpose](#purpose)
- [Scope & Boundaries](#scope--boundaries)
- [Authority (Owned Facts)](#authority-owned-facts)
- [Authoritative Inputs (Consumed Facts)](#authoritative-inputs-consumed-facts)
- [Change Rules](#change-rules)
- [Documentation Levels](#documentation-levels)
- [Owner Model](#owner-model)
- [Standard Governance Labels](#standard-governance-labels)
- [Runtime Header Rules](#runtime-header-rules)
- [Local Header Template Relationship](#local-header-template-relationship)
- [Validation Checklist](#validation-checklist)

<br>

## Purpose

- define the tracked documentation-governance model for Searcharr-nxg
- keep product docs, maintainer workflow, and local-only source material separated
- make runtime-header usage traceable without committing the local template library

## Scope & Boundaries

- This document governs tracked docs and operational artifacts in this repository.
- It does not replace project-specific technical content owned by architecture docs or runbooks.
- `.local/Template - Documentation Governance Handover.md` and `.local/Header Templates/` may be used as local source material when maintaining these rules, but they are not tracked source-of-truth documents for this repository.

## Authority (Owned Facts)

This document owns:

- the documentation level model
- the ownership model for tracked documents
- the standard governance labels used across project docs
- the header-template application rules for tracked runtime/config files

## Authoritative Inputs (Consumed Facts)

This document consumes:

- actual repository structure
- project-specific maintainer workflow in `maintainer/`
- the Searcharr-nxg architecture and reference-lineage docs in `documentation/`
- local-only governance source material in `.local/` when the maintainer chooses to use it

## Change Rules

- Normalize progressively instead of forcing destructive rewrites.
- Do not overwrite legacy docs unless the change was requested or approved.
- If a document is already aligned and high-signal, preserve it.
- Keep product architecture and reference-lineage documents concise and factual.

## Documentation Levels

Use a three-level model:

- Level 1: principle documents for global rules, standards, identity, trust, naming, and shared registries
- Level 2: `README.md` files for scope, inventory, boundaries, and navigation
- Level 3: runbooks for executable implementation, verification, update, rollback, and troubleshooting

Each mutable fact should have one owner document only.

## Owner Model

- Principle documents own rules.
- `README.md` files own inventory and boundaries.
- Runbooks own procedures.
- Runbooks may show examples, but should reference the owner document for canonical values.

## Standard Governance Labels

Use these labels where the governance model applies:

- `History`
- `Scope & Boundaries`
- `Authority (Owned Facts)`
- `Authoritative Inputs (Consumed Facts)`
- `Change Rules`

Do not replace them with near-synonyms when the standard label is intended.

## Runtime Header Rules

Operational artifacts such as:

- `docker-compose.yml`
- `.env`
- `.env.example`
- `Dockerfile`
- shell scripts
- Python scripts
- reverse-proxy configs
- systemd units

should start with a stable header block when that file type uses the header-template model.

Header blocks should capture:

- provenance or source
- purpose
- documentation reference
- important local design notes
- `History`

Rules:

- Runtime secret-bearing `.env` files should be marked `LOCAL ONLY`.
- `.env.example` files should be marked `SAFE TO COMMIT`.
- If a file was created from the local header-template library, keep the visible `Header template reference:` line in the tracked file.
- If the implemented header contract changes materially, update the file and any related tracked documentation in the same change set.

## Local Header Template Relationship

- `.local/Header Templates/` is a local mirror of header-only templates maintained in another repository.
- Leave that local mirror unchanged unless a header-template addition or contract change is explicitly requested.
- If a new file type needs a header template, the change should be treated as an upstream template-library update that may later be synced back into this workspace.
- Tracked repository files should record the implemented template reference/version where applicable, but should not duplicate the local library.

## Validation Checklist

Before considering documentation work complete, verify:

- the selected document matches the correct ownership level
- owner and consumer boundaries are clear
- tracked docs do not duplicate local-only narrative material
- runtime/config headers are consistent where the header-template model is in use
- template reference lines remain visible where applicable
