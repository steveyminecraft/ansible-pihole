---
name: ship-change
description: >-
  Branch, commit, GitHub issue (ticket), and PR for steveyminecraft/ansible-pihole.
  Use when the user asks to ship, commit, open a ticket, create a PR, or
  "branch commit pr ticket".
---

# Ship a change (branch → ticket → commit → PR)

Follow **git-branch-workflow** and **readme-maintenance** project skills.

## When the user asks to ship

Run only when explicitly requested (commit/push/PR). Never force-push `master`.

### 1. Refresh `master`

```bash
git fetch origin
git checkout master
git pull --ff-only origin master
```

If fast-forward fails, stop and ask the user.

### 2. Topic branch

```bash
git checkout -b <type>/<short-kebab-description>
```

Types: `feature/`, `fix/`, `bugfix/`, `chore/`, `docs/`.

### 3. GitHub issue (ticket)

Create before or with the PR so the PR can link it:

```bash
gh issue create \
  --title "<concise title>" \
  --body "$(cat <<'EOF'
## Problem / goal

<why this change exists>

## Proposed solution

- <bullet>

## Acceptance criteria

- [ ] <checkable item>

EOF
)"
```

Note the issue number (e.g. `#140`).

### 4. Commit

```bash
git status
git diff
git log -3 --oneline
```

Stage only relevant files. Never commit secrets (`.env`, vault blobs, `graphify-out/`).

Conventional commit subject (`feat:`, `fix:`, `docs:`, `chore:`, etc.). Body explains **why**.

```bash
git add <paths>
git commit -m "$(cat <<'EOF'
<type>: <summary>

<optional body — user-visible impact, not file list>

Fixes #<issue>
EOF
)"
```

Use `Fixes #N` or `Closes #N` when the issue should close on merge.

### 5. Push and PR

```bash
git push -u origin HEAD
```

```bash
gh pr create \
  --base master \
  --title "<type>: <summary>" \
  --body "$(cat <<'EOF'
Fixes #<issue>

## Summary

- <1-3 bullets — user-visible or explicit internal-only>

## Release notes

- Proposed release note sentence:
  - `<one sentence or N/A for internal-only>`
- Changelog type:
  - [ ] `feat`
  - [ ] `fix`
  - [ ] `perf`
  - [ ] `refactor`
  - [x] non-user-facing (`docs` / `ci` / `chore` / `test` / `build`)

## Validation

- [ ] ansible-lint / yamllint (or N/A)
- [ ] syntax checks for changed playbooks/roles (or N/A)
- [ ] Molecule / remote tests when behavior changes (or N/A)
- [ ] README / docs updated when needed

## Scope and risk

- Risk level: [x] low  [ ] medium  [ ] high
- Rollback plan: revert PR merge commit

EOF
)"
```

Return the **issue URL** and **PR URL** to the user.

### 6. After merge (later)

Per git-branch-workflow: delete merged topic branch locally and on origin.

## Checklist

```
- [ ] master fast-forwarded from origin
- [ ] topic branch from master
- [ ] GitHub issue created
- [ ] conventional commit; no secrets in diff
- [ ] README updated if setup/behavior docs changed
- [ ] PR targets master; links issue
- [ ] PR body matches .github/pull_request_template.md
```

## Repo-specific notes

- PRs merge to **`master`** only.
- Release notes matter: PR title should match conventional commit format (CI checks PR titles).
- `graphify-out/` is gitignored — never add it.
