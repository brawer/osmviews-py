<!--
SPDX-FileCopyrightText: 2026 Sascha Brawer <sascha@brawer.ch>
SPDX-License-Identifier: MIT
-->

# Contributing to osmviews-py 👋

Thanks for looking! This is a small, focused package and contributions of every
size are welcome — a typo fix, a clearer doc sentence, a missing test case, a bug
report, or a new feature. No contribution is too small. 🙂

## Setting up a development environment

This project uses [uv](https://docs.astral.sh/uv/). Install it if you haven’t
already:

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then clone the repository and check your setup:

```sh
git clone https://github.com/brawer/osmviews-py.git
cd osmviews-py
uv run pytest
uv run ruff check
uv run ruff format --check
```

CI runs the same checks on Python 3.11, 3.12 and 3.13, and requires `ruff check`
and `ruff format --check` to be clean.

## Making changes

- Keep changes focused; one topic per pull request.
- Add or update tests for any changed behaviour.
- Run `uv run pytest && uv run ruff check && uv run ruff format` before opening a
  pull request.
- If you change dependencies, run `uv lock` and commit the updated `uv.lock`.
- If you touch `.github/workflows/`, run `uvx zizmor .github/workflows/` — CI
  enforces it (SHA-pinned actions and other workflow-security rules).

## Running the tests against the real dataset 🌍

Most tests build tiny synthetic GeoTIFFs and need nothing extra. The end-to-end
test in `tests/test_online.py` runs against the real ~594 MB dataset and is
skipped by default. To run it, fetch the file and point the test at it:

```sh
curl -fSL -o osmviews.tiff https://osmviews.toolforge.org/download/osmviews.tiff
OSMVIEWS_TIFF="$PWD/osmviews.tiff" uv run pytest
```

`osmviews.tiff` in the repository root is picked up automatically (and is
git-ignored).

## Running the micro-benchmarks 📈

```sh
uv run python benchmarks/bench.py
```

It builds a synthetic GeoTIFF and prints `ns/call` for a cache hit and for the
re-decode path. Informational, not pass/fail.

## Commit and PR style 📝

We use [Conventional Commits](https://www.conventionalcommits.org) for pull
request titles (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `perf:`,
`build:`, `chore:`, `ci:`), and CI checks the PR title. PRs are squash-merged, so
the title becomes the commit message on `main` and feeds the changelog. Releases
are cut by [release-please](https://github.com/googleapis/release-please) — see
[RELEASING.md](RELEASING.md).

Please keep changes focused, add tests for behaviour changes, and credit any
sources you adapt code or data from.

## Reporting issues and asking questions 🤝

Open an issue on GitHub. For anything sensitive, or to report a Code of Conduct
concern, email Sascha (sascha@brawer.ch). By contributing you agree that your
work is licensed under the [MIT License](LICENSE), and to abide by our
[Code of Conduct](CODE_OF_CONDUCT.md).

## Project structure

```
pyproject.toml         project metadata, build and tool configuration
src/osmviews/
  __init__.py          public API: open(), OSMViews, DOWNLOAD_URL, Metrics
  _tiff.py             hand-written OSMViews-GeoTIFF header parser
  _projection.py       WGS84 -> Web Mercator pixel projection
  _cache.py            decoded-tile LRU cache and the Metrics dataclass
tests/
  _fixtures.py         builder for synthetic OSMViews-shaped GeoTIFFs
  test_*.py            unit tests
benchmarks/bench.py    dependency-free micro-benchmarks
.github/workflows/     CI, release-please, publish, CodeQL, Scorecard, pip-audit
```
