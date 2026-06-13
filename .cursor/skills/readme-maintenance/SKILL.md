---
name: readme-maintenance
description: >-
  Requires keeping README.md files in steveyminecraft/ansible-pihole accurate
  whenever code, config, CI, Molecule, setup, or behavior changes. Use on every
  implementation task in this repository, before finishing work or opening a PR.
---

# README maintenance (ansible-pihole)

**READMEs must stay up to date at all times.** Treat README updates as part of the same change—not a follow-up.

Also apply the **readme-change-log** user skill when editing this repo. This file adds repo-specific scope.

## Files to maintain

| File | Update when |
|------|-------------|
| `README.md` (repo root) | Playbooks, roles, install, Molecule scenarios, CI, inventory, scripts, Galaxy/meta, supported OS versions, branch/workflow notes |
| `roles/unbound/README.md` | Unbound role behavior, variables, images, or usage |

If you add a new role with its own `README.md`, keep that file current too.

## When to edit (non-exhaustive)

Update README(s) in the **same commit/PR** as the functional change when you touch:

- `.github/workflows/` or Actions under `.github/actions/`
- `molecule/` (scenarios, boxes, providers, test sequence)
- `playbooks/`, `inventory/`, `roles/`
- `scripts/` users run (`install-ansible-collections.sh`, `molecule-vagrant`, etc.)
- `meta/main.yml` (Galaxy platforms, versions)
- Dependencies (`roles/requirements.yml`, `collections/requirements.yml`)

Skip README edits only if the user explicitly says not to, or the change is purely internal with zero user-visible effect (rare—when in doubt, update).

## Where to put updates

Match existing root `README.md` sections:

- **Setup / requirements** — Python 3.13 or 3.14, ansible-core 2.20.x, venv/`requirements.txt`, Vagrant, Galaxy collections
- **Molecule integration tests** — scenarios, boxes (e.g. Ubuntu version), provider/inventory env vars
- **CI** — what workflows run and on which branches
- **Usage / playbooks** — commands, tags, inventory paths

Prefer **editing stale text in place** over duplicating. Remove wrong version numbers (e.g. old Ubuntu box names) when replacing with new ones.

## Completion check (every task)

Before marking work done or suggesting a PR:

```
- [ ] Root README.md reflects the change (or consciously N/A)
- [ ] Role README(s) updated if role behavior/docs changed
- [ ] No contradictions (old platform versions, removed scripts, wrong branch names)
```

Include README changes in the topic-branch PR to `master`, not a separate doc-only PR unless the user requests that.
