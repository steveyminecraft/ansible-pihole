---
name: git-branch-workflow
description: >-
  Defines steveyminecraft/ansible-pihole Git branch promotion:
  topic branch → dev → master. Use when creating branches, merging, opening
  PRs, syncing dev with master, or any git workflow in this repository.
---

# ansible-pihole Git branch workflow

## Branch flow

```
<topic-branch>  →  dev  →  master
```

- **Topic branches** (`feature/*`, `bugfix/*`, `fix/*`, `chore/*`, etc.): all implementation work happens here.
- **`dev`**: integration branch; topic branches merge here first.
- **`master`**: release/production line; only promoted from `dev` (except emergency hotfixes—then sync `dev` back).

Do **not** land feature work directly on `master`. Do **not** long-lived development on `dev` without a topic branch when the change is non-trivial.

## Agent rules

1. **Start new work only after refreshing local `master` and `dev` from the current remote `master`**:
   ```bash
   git fetch origin
   git checkout master
   git pull --ff-only origin master
   git checkout dev
   git pull --ff-only origin dev
   git merge --ff-only master
   git checkout -b feature/short-description   # or bugfix/, fix/, chore/
   ```
   If `dev` cannot fast-forward to `master`, stop and ask the user how to reconcile before creating the topic branch.

2. **Merge direction** (one way):
   - Topic branch → `dev` (PR preferred)
   - `dev` → `master` (PR preferred)
   - Never merge `master` into a topic branch for “latest code” unless resolving a specific conflict—prefer rebasing the topic branch onto `dev` after syncing `dev` with `master`.

3. **Before starting work**, always verify local `master` and `dev` are current:
   ```bash
   git fetch origin
   git checkout master
   git pull --ff-only origin master
   git checkout dev
   git pull --ff-only origin dev
   git merge --ff-only master
   git status -sb
   ```
   If fast-forward is not possible, stop and ask the user how to reconcile (do not force-push).

4. **After `master` moves** (release merge, hotfix), bring `dev` current the same way (fast-forward when `dev` has no unique commits).

5. **PR targets**:
   - Topic branch → **`dev`**
   - `dev` → **`master`**

6. **After a topic branch is merged**, delete it locally and remotely to keep repo hygiene:
   ```bash
   git fetch origin --prune
   git checkout dev
   git pull --ff-only origin dev
   git branch -d feature/short-description
   git push origin --delete feature/short-description
   git fetch origin --prune
   ```
   Use `git branch -d` for merged branches. Use `git branch -D` only after confirming the branch is merged or intentionally abandoned.

7. **Commits**: only when the user asks. Do not push unless asked.

8. **READMEs**: keep root and role READMEs current in the same change set. See **readme-maintenance** project skill.

## CI context

GitHub Actions (`.github/workflows/ci.yml`) run on push/PR to `dev`, `master`, and pushes to `feature/**`. Topic branches get CI before merge to `dev`.

## Quick checklist

```
- [ ] local master is fast-forwarded to origin/master
- [ ] local dev is fast-forwarded to origin/dev
- [ ] dev is synced with current master before branching
- [ ] branch created from dev
- [ ] changes merged to dev via PR
- [ ] merged topic branch deleted locally
- [ ] merged topic branch deleted from origin
- [ ] dev promoted to master via PR
- [ ] after master release: dev fast-forwarded to master
- [ ] README(s) updated (see readme-maintenance skill)
```
