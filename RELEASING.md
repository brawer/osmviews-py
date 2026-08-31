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
   `.release-please-manifest.json`. It runs as the **release-please-bot** GitHub
   App (see [App setup](#one-time-setup)) — a workflow run started by the
   built-in `GITHUB_TOKEN` cannot itself start further workflow runs, so the App
   identity is what lets the release PR’s CI run and the tag launch
   `publish.yml`.
3. Review that PR and squash-merge it when you want to cut the release.
   release-please then pushes the `vX.Y.Z` tag and creates the GitHub release.
4. The tag push launches `publish.yml` automatically. (To re-run it:
   `gh workflow run publish.yml --ref vX.Y.Z`.) It then:
   - downloads the real ~594 MB dataset and runs the full test suite, including
     the otherwise-skipped `tests/test_online.py`;
   - checks the ref matches `pyproject.toml`;
   - builds the sdist and wheel with `uv build`;
   - attests their **SLSA build provenance** with `actions/attest-build-provenance`
     (Sigstore-signed, keyed to the artifact digests, kept in this repo’s
     attestation store — not attached to the release, which is immutable);
   - **waits for you to approve the `pypi` deployment** (the environment has a
     required reviewer and is limited to `v*` tags), then publishes to PyPI via
     **Trusted Publishing** (short-lived OIDC token, no stored secret) with a
     **PEP 740 attestation**.

The GitHub release itself is **immutable** (repo setting): once published, its
tag, commit and assets are frozen and GitHub adds its own signed release
attestation. That is why a botched release (e.g. `v0.2.0`, which never reached
PyPI) can only be superseded by a new version, never re-tagged.

## Choosing the version number

release-please picks the bump from the commit types since the last release:
`fix:` → patch, `feat:` → minor, and a `!` after the type or a `BREAKING CHANGE:`
footer → a breaking bump. While the package is `0.x` (pre-1.0), `bump-minor-pre-major`
maps a breaking change to a **minor** bump (`0.1.z` → `0.2.0`) and everything
else to a **patch** bump.

Only `feat:`, `fix:` and `perf:` commits cut a release (and appear in
`CHANGELOG.md`). `docs:`, `refactor:`, `test:`, `build:`, `ci:` and `chore:`
(including Dependabot's `chore(deps):`) are silent — they ride along with the
next real release. Use `Release-As:` if you need to ship one of those alone.

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
- The `main` ruleset requires the `ruff`, `test (Python 3.11/3.12/3.13)` and
  `pr-title` checks and squash-only merges.
- **`release-please-bot` GitHub App** — `release-please.yml` authenticates as
  this App so its PR and tag can trigger CI:
  1. Create the App at
     <https://github.com/settings/apps/new> (a personal App is fine). Homepage
     URL: the repo URL. Uncheck **Webhook → Active**. **Repository permissions**:
     `Contents: Read and write`, `Pull requests: Read and write`; nothing else.
     “Where can this GitHub App be installed?” → **Only on this account**.
  2. On the App page: **Generate a private key** (downloads a `.pem`), and note
     the **Client ID** (shown near the top, `Iv23…`).
  3. **Install App** → select `brawer/osmviews-py` only.
  4. In the repo, **Settings → Secrets and variables → Actions**:
     add a **variable** `RELEASE_PLEASE_APP_CLIENT_ID` (the Client ID) and a
     **secret** `RELEASE_PLEASE_APP_PRIVATE_KEY` (the full `.pem` contents).
     Until the variable exists, the `release-please` workflow is skipped.
  5. Delete the local `.pem`. To rotate, generate a new key and update the
     secret; App tokens themselves are short-lived and auto-refreshed per run.

## Verifying a release

```sh
# The PEP 740 attestation is shown automatically on the PyPI release page.

# SLSA build provenance for a downloaded artifact:
pip download osmviews==X.Y.Z --no-deps --no-binary :all: -d .
gh attestation verify osmviews-X.Y.Z.tar.gz --repo brawer/osmviews-py

# The GitHub release's own attestation (tag, commit, assets):
gh release verify vX.Y.Z --repo brawer/osmviews-py
```
