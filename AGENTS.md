## Tracking

- **Planning and work items** are GitHub issues in `jonocodes/lastbook-kit`, through the `gh` CLI. The pinned issue labelled `roadmap` is the checklist. Update issues rather than adding plan files to the repo.
- **Triage labels:** `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. `parked` means deliberately postponed.
- **The README** is the source of truth for what the project is. `docs/findings.md` holds dated research.

## This repo is public

- Write upstream issues and PRs inside code formatting (`` `Immortal-Protocols/lastbook#135` ``) in issues, PRs and commit messages. A plain reference or URL adds a "mentioned" entry to the upstream issue's timeline.
- No personal or household details: machine names, local paths, networks, accounts.

## Upstream

Lastbook (`Immortal-Protocols/lastbook`, MIT) is used unmodified at a pinned commit. Changes to its behaviour go in `lbx/overlay/` as small, named patches. Each one should say why it exists.
