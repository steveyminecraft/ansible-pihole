---
name: git-branch-workflow
description: >-
  Defines steveyminecraft/ansible-pihole Git branch flow:
  topic branch → master. Use when creating branches, merging, opening
  PRs, or any git workflow in this repository.
---

# ansible-pihole Git branch workflow

## Branch flow

```
<topic-branch>  →  master
```

- **Topic branches** (`feature/*`, `bugfix/*`, `fix/*`, `chore/*`, etc.): all implementation work happens here.
- **`master`**: integration + release/production branch.

Do **not** do long-lived development directly on `master` when the change is non-trivial.

## Agent rules

1. **Start new work only after refreshing local `master` from remote `master`**:
   ```bash
   git fetch origin
   git checkout master
   git pull --ff-only origin master
   git checkout -b feature/short-description   # or bugfix/, fix/, chore/
   ```

2. **Merge direction** (one way):
   - Topic branch → `master` (PR preferred)
   - Never merge `master` into a topic branch for “latest code” unless resolving a specific conflict—prefer rebasing the topic branch onto `master`.

3. **Before starting work**, always verify local `master` is current:
   ```bash
   git fetch origin
   git checkout master
   git pull --ff-only origin master
   git status -sb
   ```
   If fast-forward is not possible, stop and ask the user how to reconcile (do not force-push).

4. **After `master` moves** (release merge, hotfix), rebase active topic branches onto `master` as needed.

5. **PR targets**:
   - Topic branch → **`master`**

6. **After a topic branch is merged**, delete it locally and remotely to keep repo hygiene:
   ```bash
   git fetch origin --prune
   git checkout master
   git pull --ff-only origin master
   git branch -d feature/short-description
   git push origin --delete feature/short-description
   git fetch origin --prune
   ```
   Use `git branch -d` for merged branches. Use `git branch -D` only after confirming the branch is merged or intentionally abandoned.

7. **Commits**: only when the user asks. Do not push unless asked.

8. **READMEs**: keep root and role READMEs current in the same change set. See **readme-maintenance** project skill.

## CI context

GitHub Actions (`.github/workflows/ci.yml`) run on push/PR to `master`, and pushes to `feature/**`. Topic branches get CI before merge to `master`.

## Quick checklist

```
- [ ] local master is fast-forwarded to origin/master
- [ ] branch created from master
- [ ] changes merged to master via PR
- [ ] merged topic branch deleted locally
- [ ] merged topic branch deleted from origin
- [ ] README(s) updated (see readme-maintenance skill)
```
