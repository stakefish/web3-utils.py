# web3-utils

Internal Web3 utilities for Python


# Installation
Install dependencies

```bash
make install
```


# Code formatting

```bash
make format
```

# Releasing

Before releasing a new version, build and test the package that will be released. There’s a script to build and install the wheel locally, then generate a temporary virtualenv for smoke testing:

```bash
pip install --upgrade build
```

```bash
make package
```

The library will be published to PyPI. You must [create an account](https://pypi.org/account/register/) to be able publish the new artifacts.

## Push The Release to GitHub

After committing the compiled release notes and pushing them to the master branch, release a new version:

```bash
make release bump=$$VERSION_PART_TO_BUMP$$
```

## Which Version Part to Bump

The version format for this repo is `{major}.{minor}.{patch}` for stable, and `{major}.{minor}.{patch}{stage}.{devnum}` for unstable (stage can be `beta` or `rc`).

During a release, specify which part to bump, like `make release bump=minor` or `make release bump=devnum`.

If you are in an beta version, `make release bump=stage` will bump to `rc`. If you are in a `rc` version, `make release bump=stage` will bump to a stable version.
