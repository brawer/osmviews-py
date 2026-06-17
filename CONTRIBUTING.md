# Contributing to osmviews-py

## Setting up a development environment

This project uses [uv](https://docs.astral.sh/uv/) for dependency management
and building. Install it if you haven’t already:

```shell
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then clone the repository and run the tests to verify your setup:

```shell
git clone https://github.com/brawer/osmviews-py.git
cd osmviews-py
uv run --with pytest pytest
```

## Making changes

- Keep changes focused; one topic per pull request.
- Add or update tests for any changed behavior.
- Make sure `uv run --with pytest pytest` passes before opening a pull request.

Tests also run automatically on every push and pull request via GitHub Actions.

## Release workflow

Releases are published to [PyPI](https://pypi.org/project/osmviews/) automatically
by GitHub Actions when a version tag is pushed. The steps are:

**1. Update the version in `pyproject.toml`:**

```toml
[project]
version = "0.2.0"
```

Follow [Semantic Versioning](https://semver.org): increment the patch version
for bug fixes, the minor version for new features, and the major version for
breaking changes.

**2. Commit the version bump:**

```shell
git commit -am "Release 0.2.0"
```

**3. Tag the commit:**

```shell
git tag v0.2.0
```

The tag must start with `v` and match the version in `pyproject.toml` exactly
(e.g. tag `v0.2.0` for version `0.2.0`). The GitHub Actions workflow verifies
this and will fail if they don’t match, preventing a mismatched release from
being published.

**4. Push the commit and tag:**

```shell
git push --follow-tags
```

GitHub Actions will then run the tests, build the source distribution and
wheel, and publish them to PyPI using trusted publishing (no API token
required). You can monitor the workflow run under the
[Actions tab](https://github.com/brawer/osmviews-py/actions).


## Project structure

```
pyproject.toml      project metadata and build configuration
src/osmviews/       library source code
tests/              unit tests
.github/workflows/  CI/CD workflows (test, build, publish)
```
