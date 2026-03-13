---
name: github-gaant-project
description: Use when working in this repository to understand or operate GitHub Gaant features, CLI commands, YAML sync flows, planning-to-Gaant workflows, issue-thread exports, or monthly user issue exports. Covers how the project stores data, which commands to run, and which files to inspect before making changes.
---

# GitHub Gaant Project Skill

Use this skill when the task is about this repository's product behavior or how to operate its CLI safely.

## What This Project Does

`github-gaant` syncs GitHub Issues and GitHub Projects V2 with a local YAML file, then generates Mermaid views and issue export markdown.

Current scope:
- YAML only. Excel support was removed.
- GitHub Project V2 dates are handled through GraphQL.
- Issue CRUD and search/export flows use REST via PyGithub.

## Start Here

1. Read [README.md](../../../README.md) for the command map and file layout.
2. If the task is about planning documents, also read:
   - `.agent/workflows/doc-to-planning.md`
   - `.agent/workflows/planning-to-gaant.md`
3. If the task is about implementation details, inspect only the relevant module:
   - CLI: `github_gaant/cli.py`
   - Sync logic: `github_gaant/sync.py`
   - REST search/export logic: `github_gaant/github_rest.py`
   - GraphQL project sync: `github_gaant/github_graphql.py`
   - YAML format: `github_gaant/parsers/yaml_parser.py`

## Operational Rules

- Prefer running commands through the local environment: `.venv/bin/python -m github_gaant.cli ...`
- Load credentials from `.env`; `GITHUB_TOKEN` is required.
- `config.yaml` is the default source for repo/project scope unless a command explicitly overrides it.
- `gaant pull` treats GitHub as source of truth and rewrites local generated artifacts.
- `gaant push` reads `issues/<number>.md` when present and can update issue bodies from those files.
- `gaant list-referenced-users` scans issues in a repo or org and aggregates GitHub users who were mentioned or assigned.
- Monthly user export uses explicit scope:
  - `--repo owner/repo` is more specific
  - `--org org-name` scans the organization
  - if neither is given, commands may fall back to `config.yaml`

## Important Behaviors

- New tasks are created with `issue: 0` in `gaant.yaml`.
- Hierarchy is represented with `subtasks`.
- Markdown issue-thread exports include:
  - issue body
  - all comments
  - timeline events/interactions when available
- Referenced-user discovery counts:
  - users mentioned in issue body
  - users mentioned in comments
  - users assigned on the issue or through assignment events
- Monthly export output directory includes the selected scope:
  - org example: `lmatas-2026-2-LA-Referencia-IOI`
  - repo example: `lmatas-2026-2-LA-Referencia-IOI-a_planning_semantic`

## When Editing

- Keep docs and CLI behavior aligned.
- Preserve YAML-only assumptions unless the user explicitly wants a format change.
- Add or update tests for any change in filtering, export naming, date handling, or sync semantics.
