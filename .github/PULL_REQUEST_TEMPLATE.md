<!--
SPDX-FileCopyrightText: 2026 Sascha Brawer <sascha@brawer.ch>
SPDX-License-Identifier: MIT
-->

<!--
Title this PR in Conventional Commits style, e.g. “fix: wrap longitude at the
antimeridian”. CI checks the title, and it becomes the squash-merge commit
message and feeds the changelog. Add “!” (e.g. “feat!: …”) for a breaking
change.
-->

## What and why



## Checklist

- [ ] `uv run pytest` passes (and new behaviour has a test)
- [ ] `uv run ruff check` and `uv run ruff format --check` are clean
- [ ] Public API changes are documented and marked breaking if they are
- [ ] `uv.lock` is updated if dependencies changed
- [ ] Sources for any adapted code or data are credited
