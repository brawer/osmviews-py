<!--
SPDX-FileCopyrightText: 2026 Sascha Brawer <sascha@brawer.ch>
SPDX-License-Identifier: MIT
-->

# Releasing

Releases are automated with
[release-please](https://github.com/googleapis/release-please) and published to
[PyPI](https://pypi.org/project/osmviews/) by GitHub Actions.

## How it works

1. Every pull request has a [Conventional Commits](https://www.conventionalcommits.org)
   title (`feat:`, `fix:`, `docs:`, `perf:`, `refactor:`, `test:`, `build:`,
   `ci:`, `chore:`). PRs are squash-merged, so the title becomes the commit on
   `main`. A CI check enforces this.
2. `.github/workflows/release-please.yml` watches `main` and keeps a single open
   **“chore(main): release x.y.z”** pull request. It bumps the `version` in
   `pyproject.toml`, updates `CHANGELOG.md` from the commit history, and updates
   `.release-please-manifest.json`.
3. Review that PR and squash-merge it when you want to cut the release.
   release-please then pushes the `vX.Y.Z` tag and creates the GitHub release.
4. The tag triggers `.github/workflows/publish.yml`, which:
   - downloads the real ~594 MB dataset and runs the full test suite, including
     the otherwise-skipped `tests/test_online.py`;
   - checks the tag matches `pyproject.toml`;
   - builds the sdist and wheel with `uv build`;
   - generates **SLSA v1.0 Build Level 3** provenance
     (`multiple.intoto.jsonl`, attached to the GitHub release) via the SLSA
     project’s isolated reusable workflow;
   - **waits for you to approve the `pypi` deployment** (the environment has a
     required reviewer and only runs for `v*` tags), then publishes to PyPI via
     **Trusted Publishing** (short-lived OIDC token, no stored secret) with
     **PEP 740 attestations**.

## Choosing the version number

release-please picks the bump from the commit types since the last release:
`fix:` → patch, `feat:` → minor, and a `!` after the type or a `BREAKING CHANGE:`
footer → a breaking bump. While the package is `0.x` (pre-1.0), `bump-minor-pre-major`
maps a breaking change to a **minor** bump (`0.1.z` → `0.2.0`) and everything
else to a **patch** bump.

The public API is: `OSMViews` and its methods, `Metrics` and its fields, `open`,
`DOWNLOAD_URL`, `FormatError`, and the documented behaviour of `rank`.

| Bump                  | When                                                                                                        |
| --------------------- | ----------------------------------------------------------------------------------------------------------- |
| `0.x.0` → `0.x.(y+1)` | Backwards-compatible: bug fixes, new public items, more permissive behaviour, doc changes, dependency bumps. |
| `0.x.0` → `0.(x+1).0` | Anything a caller could notice: removing/renaming a public item, changing a signature, changing `rank()`’s output, tightening input handling, raising the minimum Python version. |

To force a specific version, put `Release-As: 1.0.0` in a commit body.

## One-time setup

Already configured on this repository (listed here in case it needs rebuilding):

- **PyPI Trusted Publisher** for `osmviews`: owner `brawer`, repository
  `osmviews-py`, workflow `publish.yml`, environment `pypi`
  (<https://pypi.org/manage/project/osmviews/settings/publishing/>).
- **GitHub `pypi` environment**: required reviewer `brawer`, deployments limited
  to `v*` tags.
- **Settings → Actions → General → Workflow permissions**: “Allow GitHub Actions
  to create and approve pull requests” is enabled (release-please opens the
  release PR).
- The `main` ruleset requires the `ruff`, `test (Python 3.11/3.12/3.13)` and
  `pr-title` checks and squash-only merges.

## Verifying a release

```sh
# PEP 740 attestations are shown automatically on the PyPI release page.

# SLSA provenance:
pip download osmviews==X.Y.Z --no-deps --no-binary :all: -d .
gh release download vX.Y.Z --repo brawer/osmviews-py --pattern 'multiple.intoto.jsonl'
slsa-verifier verify-artifact osmviews-X.Y.Z.tar.gz \
  --provenance-path multiple.intoto.jsonl \
  --source-uri github.com/brawer/osmviews-py \
  --source-tag vX.Y.Z
```
