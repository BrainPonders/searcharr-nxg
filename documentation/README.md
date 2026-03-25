# Documentation

Keep only tracked project documentation here.

Use this folder for:

- public product documentation
- architecture and decision-model references
- tracked maintainer-facing operational references
- repository governance material that belongs with the project

## Governance Model

- Principle documents own rules and shared policy.
- `README.md` files own scope, inventory, and navigation.
- Runbooks own executable procedures.
- Keep each mutable fact authoritative in one place and reference that owner document elsewhere.
- Normalize existing docs progressively instead of forcing destructive rewrites.

## Index

- `documentation/Documentation Governance Principles.md`
  - tracked rules for documentation ownership and runtime header usage
- `documentation/System Architecture.md`
  - Searcharr-nxg product model, request flow, and decision-state model
- `documentation/Reference Survey.md`
  - comparison of upstream Searcharr lineage and selective reuse boundaries

## Runtime Headers

- Operational artifacts such as compose files, `.env` files, Dockerfiles, and scripts should use stable header blocks.
- When a project uses the local header-template library, keep the visible `Header template reference:` line in the generated file.
- Treat `.local/Header Templates/` as a local source mirror only; tracked docs should describe the rule, not duplicate the local library.

Do not use this folder for:

- personal runbooks
- scratch notes
- reusable private templates
- local-only overlays

Those belong in `.local/` instead.
