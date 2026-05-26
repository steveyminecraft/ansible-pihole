# Git Branch Workflow

Use this workflow before starting implementation work so topic branches are based on the current release line and do not regress fixes already merged to `master`.

## Branch Flow

```text
topic branch -> dev -> master
```

- Create implementation branches from `dev` only after syncing local `master` and `dev`.
- Merge topic branches into `dev` first.
- Promote `dev` to `master` by PR when ready to release.
- Delete merged topic branches locally and remotely after the merge is complete.
- Do not do long-lived implementation directly on `dev` or `master`.

## Before Creating A Topic Branch

Run this from a clean or intentionally stashed worktree:

```bash
git fetch origin

git checkout master
git pull --ff-only origin master

git checkout dev
git pull --ff-only origin dev
git merge --ff-only master

git checkout -b feature/short-description
```

If `dev` cannot fast-forward or merge cleanly from `master`, stop and reconcile `dev` before creating the topic branch. Do not create a new branch from stale local refs.

## Existing Topic Branches

Before continuing work on an existing topic branch, rebase it onto the current `master` or the refreshed `dev`, depending on the PR target:

```bash
git fetch origin
git checkout master
git pull --ff-only origin master
git checkout dev
git pull --ff-only origin dev
git merge --ff-only master
git checkout feature/short-description
git rebase dev
```

After rebasing a branch that was already pushed, update the remote with `--force-with-lease`.

## After A Branch Is Merged

Keep the repository tidy by deleting merged topic branches in both places:

```bash
git fetch origin --prune
git checkout dev
git pull --ff-only origin dev
git branch -d feature/short-description
git push origin --delete feature/short-description
```

Use `git branch -d` for normal cleanup so Git refuses to delete unmerged local work. Only use `git branch -D` after confirming the branch was merged or is intentionally abandoned.

After deleting remote branches, prune stale remote-tracking refs:

```bash
git fetch origin --prune
```
