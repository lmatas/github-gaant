# GitHub Gaant Features

## Core Files

- `config.yaml`: repo/project configuration and output filename
- `.env`: must contain `GITHUB_TOKEN`
- `gaant.yaml`: editable local project/task representation
- `gaant_gantt.md`: generated Mermaid markdown
- `issues/*.md`: optional issue bodies used by `gaant push`
- `github_gaant/cli.py`: command definitions
- `github_gaant/sync.py`: YAML sync and export flows
- `github_gaant/github_rest.py`: issue search, comments, timeline events
- `github_gaant/github_graphql.py`: GitHub Projects V2 fields/items

## Main Commands

- `gaant init --repo owner/repo --project 1`
  - creates `config.yaml`
  - defaults to `gaant.yaml`

- `gaant validate`
  - checks config, token, project visibility, and date fields

- `gaant pull`
  - fetches project items from GitHub
  - writes `gaant.yaml`
  - writes `gaant_gantt.md`
  - writes `issues/<number>.md` for issue bodies

- `gaant status`
  - compares local YAML against GitHub state

- `gaant push --dry-run`
  - previews local changes

- `gaant push`
  - creates new issues for `issue: 0`
  - updates titles, labels, assignees, states, dates, and bodies
  - can enforce sub-issue links with `--enforce-subissues`

- `gaant view --format mermaid|hierarchy|table`
  - renders local YAML into a visualization

- `gaant fetch-thread ISSUE_NUMBER`
  - exports one issue with full comments to markdown

- `gaant fetch-user-issues USERNAME`
  - exports issues where the user interacted
  - supports date ranges and optional project-status exclusion

- `gaant list-referenced-users`
  - scans a repo or org and lists GitHub users mentioned or assigned in issues
  - prints aggregate counts for mentions, assignments, and total affected issues
  - examples:
    - `gaant list-referenced-users -r owner/repo`
    - `gaant list-referenced-users -O my-org`

- `gaant fetch-user-monthly -u USER -y YEAR -m MONTH`
  - exports issues where the user was mentioned or assigned during a month
  - requires scope via `--repo` or `--org`, or defaults from `config.yaml`
  - folder name includes the effective scope
  - each issue file name includes repo and issue number

## Data Conventions

- `gaant.yaml` stores:
  - `project`
  - `tasks`
  - each task may include `issue`, `title`, `start`, `end`, `assignees`, `labels`, `closed`, `subtasks`

- `issue: 0` means "create on next push"
- missing `body` in YAML means "do not compare/update body"
- existing `issues/<number>.md` overrides body during push
- empty `issues/<number>.md` means "clear body intentionally"

## Planning Workflows Already In Repo

- `.agent/workflows/doc-to-planning.md`
  - transforms raw planning docs into structured planning markdown

- `.agent/workflows/planning-to-gaant.md`
  - converts planning markdown into `gaant.yaml`
  - then pushes issues and generates `issues/*.md`

- `.agent/workflows/gaant_template.yaml`
  - reference template for YAML generation

## High-Risk Areas

- Date filtering and timezone handling in user export flows
- Sync semantics between local YAML and GitHub issue state
- Output naming for monthly exports and per-issue markdown files
- Any change that affects `config.yaml` fallback behavior

## Suggested Verification

- Run `.venv/bin/pytest -q`
- For CLI changes, also run `.venv/bin/python -m github_gaant.cli COMMAND --help`
