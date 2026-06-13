# Git Branch Workflow

Use this workflow before starting implementation work so topic branches are
based on the current release line and do not regress fixes already merged to
`master`.

## Branch Flow

```text
topic branch -> master
```

- Create implementation branches from `master` after syncing local `master`.
- Merge topic branches directly into `master`.
- Delete merged topic branches locally and remotely after the merge is complete.
- Do not do long-lived implementation directly on `master`.

## Before Creating A Topic Branch

Run this from a clean or intentionally stashed worktree:

```bash
git fetch origin

git checkout master
git pull --ff-only origin master

git checkout -b feature/short-description
```

Do not create a new branch from stale local refs.

## Existing Topic Branches

Before continuing work on an existing topic branch, rebase it onto the current
`master`:

```bash
git fetch origin
git checkout master
git pull --ff-only origin master
git checkout feature/short-description
git rebase master
```

After rebasing a branch that was already pushed, update the remote with `--force-with-lease`.

## After A Branch Is Merged

Keep the repository tidy by deleting merged topic branches in both places:

```bash
git fetch origin --prune
git checkout master
git pull --ff-only origin master
git branch -d feature/short-description
git push origin --delete feature/short-description
```

Use `git branch -d` for normal cleanup so Git refuses to delete unmerged local work. Only use `git branch -D` after confirming the branch was merged or is intentionally abandoned.

After deleting remote branches, prune stale remote-tracking refs:

```bash
git fetch origin --prune
```
