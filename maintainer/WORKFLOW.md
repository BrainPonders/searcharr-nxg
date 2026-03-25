# WORKFLOW

Tracked, project-specific maintainer workflow.

This file is intentionally short and execution-oriented. Personal narrative process, broader standards, and reusable private templates belong in `.local/` only.

## 1. Scope

This workflow covers:

- workspace structure changes
- local package bootstrap checks
- maintainer container rebuilds
- release preparation when the runtime stabilizes

This workflow does not cover:

- personal operating notes
- scratch implementation logs
- cross-project standards that belong in `.local/`
- maintenance of the local header-template source mirror except when explicitly requested

## 2. Lifecycle

1. Work on a branch.
2. Rebuild or bootstrap locally:
   - Python package checks with `searcharr-nxg --dry-run`
   - container scaffold checks with `bash maintainer/test/smoke_local_docker.sh`
3. Update tracked docs when the product model or runtime contract changes.
4. Merge according to repository policy.
5. Tag and publish only after the runtime model is stable enough to justify releases.
6. Update tracked public references if the project starts publishing version tables or image tags.

## 3. Documentation Split

- `maintainer/WORKFLOW.md` is the authoritative project workflow.
- `maintainer/development/README.md` is the local build and bootstrap guide.
- `maintainer/release/README.md` is the release and publish guide.
- `documentation/Documentation Governance Principles.md` is the tracked rule set for document ownership, structure, and runtime header usage.
- `.local/` is for personal runbooks, governance handovers, reusable private templates, header-template source material, and scratch material only.

## 4. Documentation Governance Application

- Overlay the governance model onto the current repository instead of rewriting blindly.
- Keep principle docs authoritative for shared rules and registries.
- Keep runtime/config headers consistent with the chosen header template.
- When a file is created from a local header template, retain the visible template reference line so implemented template/version usage stays traceable.
- Treat `.local/Header Templates/` as a local mirror maintained elsewhere; leave it alone unless the user explicitly asks for a header-template change.

## 5. Safety Rules

- Do not put secrets, private notes, or local-only overlays in tracked workflow docs.
- Do not assume the template defaults are correct for the real project without review.
- Keep `settings.py` local-only.
- When scripts live in nested maintainer folders, resolve the repository root from `../..`.
