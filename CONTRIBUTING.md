# Contributing

Thanks for helping improve `steveyminecraft.pihole`.

## Branching and promotion

This repository uses topic branches merged directly into `master`:

1. Create a topic branch from the latest `master`.
2. Open a PR into `master`.
3. Let release automation produce and merge the Release PR on `master`.

See `docs/git-branch-workflow.md` for the full flow and guardrails.

## Conventional commits for useful release notes

This repo uses release-please to generate `CHANGELOG.md` and GitHub release notes.
Commit subjects directly influence changelog quality.

- `feat:` for user-visible features or capability additions.
- `fix:` for user-visible bug fixes and regressions.
- `perf:` for user-visible performance improvements.
- `refactor:` for internal code structure changes that still matter to operators.
- `docs:`, `ci:`, `chore:`, `test:`, and `build:` for non-user-facing work.

Good examples:

- `fix: restore keepalived DNS health probe during failover`
- `feat: add pihole-no-unbound molecule scenario`
- `perf: reduce update playbook DNS verification retries`

Avoid vague or process-only messages such as:

- `fix: release`
- `fix: updates`
- `chore: cleanup`

## Pull request quality checklist

Before opening or merging:

- Ensure PR title and commit subjects describe user-visible impact.
- Keep formatting-only changes in their own PR where practical.
- Update `README.md` when behavior, workflows, or setup guidance changes.
- Confirm CI, linting, and (when relevant) Molecule checks pass.
- For cloud-impacting role/playbook changes, run the AWS remote workflow
  (`.github/workflows/aws-remote-tests.yml`) in `workflow_dispatch` mode.

## Templates and guardrails

- PRs use `.github/pull_request_template.md` to capture release-note details,
  validation, and risk/rollback notes.
- CI validates PR titles against conventional commit format
  (`type(scope): summary`) on pull requests.
- Optional local commit template:

  ```bash
  git config commit.template .github/commit-message-template.txt
  ```

  You can set this globally if preferred:

  ```bash
  git config --global commit.template /absolute/path/to/.github/commit-message-template.txt
  ```
