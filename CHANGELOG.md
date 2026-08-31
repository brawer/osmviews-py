<!--
SPDX-FileCopyrightText: 2026 Sascha Brawer <sascha@brawer.ch>
SPDX-License-Identifier: MIT
-->

# Changelog

All notable changes to the `osmviews` package are recorded here. This file is
maintained by [release-please](https://github.com/googleapis/release-please) from
the Conventional Commit history. Versioning follows
[Semantic Versioning](https://semver.org); while the package is pre-1.0 a bump of
the **minor** version may be breaking — see
[RELEASING.md](RELEASING.md#choosing-the-version-number).

## [0.2.0](https://github.com/brawer/osmviews-py/compare/v0.1.1...v0.2.0) (2026-08-31)


### ⚠ BREAKING CHANGES

* `rank()` returns a `0..1` score and takes `(lng, lat)`; `download()` is removed; `open()` returns the new `OSMViews` API.

### 🆕 Features

* rework to match the Rust client (0..1 ranks, no download) ([#28](https://github.com/brawer/osmviews-py/issues/28)) ([0b820bf](https://github.com/brawer/osmviews-py/commit/0b820bf55cad658dc4aed941170742361a642bdf))


### 🚧 Maintenance

* **deps-dev:** update uv-build requirement ([324f6c0](https://github.com/brawer/osmviews-py/commit/324f6c02e21f70d2d622260eb862dcad2fccead2))
* **deps-dev:** update uv-build requirement ([81b75cf](https://github.com/brawer/osmviews-py/commit/81b75cf5f9bf6c4137df10e4078acd845b127f52))
* **deps-dev:** update uv-build requirement ([1b8283d](https://github.com/brawer/osmviews-py/commit/1b8283d5a534f9ecb6edb1ed46a1e136269f8cc2))
* **deps-dev:** update uv-build requirement ([acbe24f](https://github.com/brawer/osmviews-py/commit/acbe24f7d7501d51d0c3050f0e4c8d3dcec376f8))
* **deps-dev:** update uv-build requirement ([ef008d7](https://github.com/brawer/osmviews-py/commit/ef008d7a859ed81a87e854db0f74413ffa0eaaf3))
* **deps-dev:** update uv-build requirement ([12cd214](https://github.com/brawer/osmviews-py/commit/12cd2149d6ec60dd3fb389a3db29f58da603be79))
* **deps-dev:** update uv-build requirement from &lt;0.13,&gt;=0.12.3 to &gt;=0.12.7,&lt;0.13 in the python-dependencies group ([#30](https://github.com/brawer/osmviews-py/issues/30)) ([74bf7e3](https://github.com/brawer/osmviews-py/commit/74bf7e3da6009fe32689a2c57dff3d238f6b5ec2))
* **deps:** bump actions/checkout from 4 to 6 ([edbb291](https://github.com/brawer/osmviews-py/commit/edbb291b33d76344ee9100e4065481d50cc0b677))
* **deps:** bump actions/checkout from 6 to 7 ([eb9cb30](https://github.com/brawer/osmviews-py/commit/eb9cb309752561e407d426bb1d8f044156f868b9))
* **deps:** bump astral-sh/setup-uv from 5 to 7 ([071f2da](https://github.com/brawer/osmviews-py/commit/071f2da980fff15fa3e85b1ce3e332af7bf5451e))
* **deps:** bump github/codeql-action from 3 to 4 ([439c78d](https://github.com/brawer/osmviews-py/commit/439c78d6ba94f95b11f7602c6f7884695c453499))

## [0.1.1](https://github.com/brawer/osmviews-py/releases/tag/v0.1.1) (2026-07-08)

Tagged but never published to PyPI. Dependency and CI maintenance only.

## 0.0.5 and earlier

Initial PyPI releases. `osmviews.download()` fetched the GeoTIFF and
`OSMViews.rank(lat, lng)` returned the raw view-density value. See the
[GitHub releases page](https://github.com/brawer/osmviews-py/releases) for the
per-release detail.
