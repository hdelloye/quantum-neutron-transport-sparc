---
phase: 01-qollab-smoke-test-compliant-skeleton
plan: 04
subsystem: platform
tags: [github, gh-cli, repository, private, collaborators, fresh-clone, pytest, mit-license]

# Dependency graph
requires:
  - phase: 01-qollab-smoke-test-compliant-skeleton
    provides: "01-01: flat package, main.py, requirements.txt (qiskit==2.5.2), compliance tests; 01-02: MIT LICENSE, README attribution and disclosure, gh CLI install; 01-03: recorded Qollab runtime findings in docs/QOLLAB-RUNTIME.md"
provides:
  - "Private GitHub repository https://github.com/hdelloye/quantum-neutron-transport-sparc holding every Phase 1 commit on main"
  - "Remote origin (https) with main tracking origin/main; gh configured as the git credential helper for github.com"
  - "Repo-local git identity user.name 'Hippolyte Delloye' (email kept as before)"
  - "Fresh-clone proof: clone, Python 3.14.8 venv, requirements.txt + pytest==9.1.1, pytest 36 passed"
  - "STATE.md todos: flip the repository public before the v0 publish; invite teammates once named"
affects: [submission, docs, team-handoff, 06]

# Actuals (#2632)
actuals:
  tokens: 0       # Task 3 changed no tracked file (LICENSE and email kept); planning artifacts excluded as in 01-03
  tasks: 3
  commits: 0      # MEASURED from the ledger; the metadata commit lands after this SUMMARY
plan_head_before: 905508ab6e18e633c56834368e938af447681ed2
plan_head_after: 905508ab6e18e633c56834368e938af447681ed2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Push with the explicit refspec HEAD:main and verify GitHub's main sha equals local HEAD after every push"
    - "Teammate handoff is proven by a fresh https clone into a throwaway directory with its own Python 3.14 venv outside the clone"

key-files:
  created:
    - .planning/phases/01-qollab-smoke-test-compliant-skeleton/01-04-SUMMARY.md
  modified:
    - .planning/STATE.md
    - .planning/ROADMAP.md
    - .planning/REQUIREMENTS.md

key-decisions:
  - "GitHub repository hdelloye/quantum-neutron-transport-sparc is PRIVATE until the v0 publish (Hippolyte: 'private until v0'); flip to public before ~Oct 10 7:00 PM ET"
  - "No teammates invited yet (teammates=none-yet, orchestrator-proposed default); PLAT-03's collaborator clause stays open until usernames are named"
  - "Commit email and LICENSE holder line kept unchanged (orchestrator-proposed defaults, not objected to)"

patterns-established:
  - "gh auth setup-git makes private-repo https clones and pushes work without SSH keys"

requirements-completed: [PLAT-03]  # partially: GitHub + MIT + attribution done; collaborator clause open (teammates=none-yet)

coverage:
  - id: D1
    description: "Private GitHub repository created and every Phase 1 commit pushed; GitHub main equals local HEAD; license detected as MIT"
    requirement: "PLAT-03"
    verification:
      - kind: other
        ref: "R=$(gh repo view --json nameWithOwner --jq .nameWithOwner) && test \"$(gh api repos/$R/commits/main --jq .sha)\" = \"$(git rev-parse HEAD)\" && licenseInfo.key = mit && visibility = PRIVATE"
        status: pass
    human_judgment: false
  - id: D2
    description: "Fresh clone installs requirements.txt (qiskit==2.5.2) plus pytest==9.1.1 under Python 3.14 and runs pytest green"
    requirement: "PLAT-03"
    verification:
      - kind: integration
        ref: "git clone https://github.com/hdelloye/quantum-neutron-transport-sparc.git into mktemp dir; python3.14 -m venv; pip install -r requirements.txt pytest==9.1.1; python -m pytest -q -> 36 passed, exit 0"
        status: pass
    human_judgment: false
  - id: D3
    description: "Teammates invited as collaborators"
    requirement: "PLAT-03"
    verification:
      - kind: other
        ref: "gh api repos/hdelloye/quantum-neutron-transport-sparc/invitations -> empty; collaborators -> hdelloye only (teammates=none-yet)"
        status: fail
    human_judgment: true
    rationale: "No teammate usernames exist yet; inviting is blocked on Hippolyte naming them. Exact invite command recorded as a STATE.md todo"

# Metrics
duration: 3min
completed: 2026-10-10
status: complete
---

# Phase 1 Plan 04: GitHub repository and fresh-clone handoff Summary

**Phase 1 history is now in a private GitHub repository, https://github.com/hdelloye/quantum-neutron-transport-sparc. GitHub's main equals local HEAD and GitHub detects the MIT license. A fresh https clone with its own Python 3.14 venv installs qiskit==2.5.2 and pytest==9.1.1 and passes 36 tests. No teammates have been invited because none are named yet, so PLAT-03's collaborator clause stays open.**

## Performance

- **Duration:** about 3 min of executor time for Task 3. Hippolyte's time at the Task 1 and Task 2 gates was not measured.
- **Started (Task 3):** 2026-10-10T20:07:29Z
- **Completed:** 2026-10-10T20:10Z
- **Tasks:** 3 (two human gates resolved by Hippolyte, one auto)
- **Files modified:** 0 tracked project files. Only planning artifacts and repo-local git config changed.

## Accomplishments

- Repository: **https://github.com/hdelloye/quantum-neutron-transport-sparc**. Visibility **PRIVATE**, default branch `main`, description "QAE vs classical Monte Carlo neutron transport through a SPARC first wall (Qollab x IonQ hackathon)". GitHub generated no README, license or gitignore.
- Remote: `origin` = `https://github.com/hdelloye/quantum-neutron-transport-sparc.git`. Pushed with `git push -u origin HEAD:main`, so `main` tracks `origin/main`.
- Post-push verify at the first push: GitHub `main` sha = local HEAD = `905508ab6e18e633c56834368e938af447681ed2`. `licenseInfo.key` = `mit`. Visibility prints `PRIVATE`, which matches private-until-v0. The check was run again after the final metadata push (see the orchestrator report).
- Collaborators: none invited (teammates=none-yet). `repos/.../invitations` is empty and `repos/.../collaborators` lists only `hdelloye`.
- Fresh clone (`mktemp -d` in the session scratchpad): cloned via https at HEAD `905508a`, created a `python3.14 -m venv` (3.14.8) outside the clone, installed `-r requirements.txt pytest==9.1.1` (qiskit 2.5.2, pytest 9.1.1). `python -m pytest -q` gave **36 passed, 1 warning, exit 0**. The warning is the expected `Option noise_model is not used by this backend` from the kwarg case of the IonQ-like fake.
- `gh auth setup-git` was run, so `~/.gitconfig` now has `!/opt/homebrew/bin/gh auth git-credential` for github.com and private https clones and pushes work.
- Repo-local identity: `git config --local user.name` = `Hippolyte Delloye`. `user.email` is unset locally (email=keep). Earlier commits were not rewritten.

## Checkpoint resolution

**Task 1 (human-action, GitHub CLI login).** Hippolyte ran the device-code login. The orchestrator then checked `gh auth status`, which showed "Logged in to github.com account hdelloye (keyring)" over https with scopes gist, read:org, repo and workflow. It also ran `gh api user --jq .login`, which returned `hdelloye`. Hippolyte's resume signal, verbatim: `done`. He did not run `gh auth setup-git`, so the executor ran it before pushing (it needs no human input).

**Task 2 (decision, blocking-human, publication).**
- Hippolyte's reply, verbatim: `private until v0`
- Resolved decision line: `private-until-v0; repo=quantum-neutron-transport-sparc; teammates=none-yet; email=keep; license=keep`
- Hippolyte gave only the visibility. The orchestrator proposed the other fields (repository name, teammates none-yet, email keep, license keep) as defaults in its checkpoint reply. Hippolyte did not object and answered "done", so those defaults were applied. They are orchestrator-proposed, not Hippolyte's own words.
- Hippolyte accepted that the push publishes the `.planning/` history, `.claude/CLAUDE.md` and the hostname author email to the private repository. The same content becomes public when the repository is flipped.

## Pre-push checks (verify 1)

All passed before `gh repo create`:
- `git remote` was empty.
- The tracked tree was clean outside `.planning`.
- No tracked PDF.
- `.venv/bin/python -m pytest -q` gave 36 passed. This includes the 2,000,000-byte and whitespace-path gates.
- `git grep` found no GitHub-token-shaped string (`gh[pousr]_[A-Za-z0-9]{20,}`).
- The repository name was confirmed free with `gh repo view`, which failed with "Could not resolve".

## Task Commits

1. **Task 1: Hippolyte signs the GitHub CLI into his account**: no commit (checkpoint)
2. **Task 2: Hippolyte decides how the repository is published**: no commit (checkpoint)
3. **Task 3: Create and push the repository, invite teammates, prove a fresh clone runs pytest green**: no commit. No tracked file changed: LICENSE was kept, the identity is in `.git/config`, and the repository, remote and push are external.

**Plan metadata:** the docs(01-04) commit that adds this SUMMARY and the STATE, ROADMAP and REQUIREMENTS updates. It is pushed to `origin main` afterwards so GitHub holds the full Phase 1 record.

## Files Created/Modified

- `.planning/phases/01-qollab-smoke-test-compliant-skeleton/01-04-SUMMARY.md`: this record
- `.planning/STATE.md`: decisions, plus two todos (flip the repository public, invite teammates), position 4 of 4
- `.planning/ROADMAP.md`: plan progress for 01-04
- `.planning/REQUIREMENTS.md`: PLAT-03 status, with a note that the collaborator clause is open
- `.git/config` (untracked, local): `user.name`, remote `origin`, `branch.main` upstream

## Decisions Made

- The repository stays private until the v0 publish. Before about Oct 10, 7:00 PM ET, run `gh repo edit hdelloye/quantum-neutron-transport-sparc --visibility public --accept-visibility-change-consequences` (STATE.md todo). Phase 6 adds this link to the Qollab Project Card (DOCS-07). Judges cannot open the link while it is private.
- Invites are deferred until teammates are named. For each username, run `gh api -X PUT repos/hdelloye/quantum-neutron-transport-sparc/collaborators/{username} -f permission=push`: 201 means invitation created, 204 means already a collaborator, and a 404 should be reported rather than guessed. This is a STATE.md todo.
- LICENSE keeps `Copyright (c) 2026 Hippolyte Delloye and contributors`. New commits keep git's default email.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Ran `gh auth setup-git` before pushing**
- **Found during:** Task 3, before the push
- **Issue:** Task 1 step 2 (`gh auth setup-git`) had apparently not been run, since `credential.helper` was empty. Without it, git over https could not authenticate the push or clone the private repository.
- **Fix:** Ran `gh auth setup-git`. It needs no human, and the orchestrator asked for it.
- **Files modified:** `~/.gitconfig` (user-level, outside the repo)
- **Verification:** the push succeeded and the fresh https clone of the private repository succeeded.

### Other differences from the plan text

- `requirements-completed: [PLAT-03]` is partial. The GitHub, MIT LICENSE and attribution parts are met. The collaborator part is open because teammates=none-yet, as the plan's flagged assumption says. Phase verification should report it as a gap.
- The plan's interface table lists `all_ones(n)`, which 73a4cb7 removed. This plan never calls it, so it was ignored.

**Total deviations:** 1 auto-fixed (Rule 3)
**Impact on plan:** None on scope. The push and private clone needed it.

## Issues Encountered

- None blocking. In zsh, `${PIPESTATUS[0]}` is empty, so the fresh-clone pytest was re-run with an explicit `$?` capture. It exited 0.

## User Setup Required

- **Before the v0 publish:** flip the repository public with `gh repo edit hdelloye/quantum-neutron-transport-sparc --visibility public --accept-visibility-change-consequences`.
- **When teammates are known:** invite each one with `gh api -X PUT repos/hdelloye/quantum-neutron-transport-sparc/collaborators/{username} -f permission=push`. Each invitee must accept.

## Next Phase Readiness

- Teammates can clone, install and test as soon as they are invited, or as soon as the repository is public.
- Phase 6 (DOCS-07) adds https://github.com/hdelloye/quantum-neutron-transport-sparc to the Qollab Project Card. The Qollab project is at https://qollab.xyz/u/hdelloye/quantum-neutron-transport-spar.
- Open: PLAT-03 collaborator clause (no usernames yet). Visibility flip due before v0.

## Self-Check: PASSED

- FOUND: .planning/phases/01-qollab-smoke-test-compliant-skeleton/01-04-SUMMARY.md
- FOUND: remote origin https://github.com/hdelloye/quantum-neutron-transport-sparc.git
- FOUND: GitHub main sha 905508a == local HEAD at first push; license mit; visibility PRIVATE
- FOUND: fresh-clone pytest exit 0 (36 passed)
