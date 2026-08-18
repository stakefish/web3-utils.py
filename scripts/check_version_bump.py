"""Fail a pull request that changes packaged code without bumping the release version.

Releases are cut by pushing a tag, and a tag can only ever be published once. Catching an unbumped or
inconsistent version here — while the change is still under review — is the difference between a
one-line fix and a botched release that can never be replaced on PyPI.

Usage: check_version_bump.py <base-ref>
"""

import configparser
import subprocess
import sys

# Only these decide what a consumer installs. A PR touching CI, tests or docs releases nothing, so
# demanding a bump for it would train people to bump meaninglessly.
PACKAGED_PATHS = ("web3_utils/", "setup.cfg", "pyproject.toml", "requirements.txt")
SKIP_LABEL = "skip-version-check"


def _run(*args: str) -> str:
    return subprocess.run(args, capture_output=True, text=True, check=True).stdout.strip()


def _version_from(text: str, section: str, option: str) -> str:
    parser = configparser.ConfigParser()
    parser.read_string(text)
    return parser.get(section, option).strip()


def _as_tuple(version: str) -> tuple:
    # Deliberately not packaging.version: this repo's bumpversion serialize can emit `0.12.0b.1`, which
    # is not PEP 440 and would raise rather than compare. Numeric parts are enough to order releases.
    return tuple(int(part) for part in version.split(".") if part.isdigit())


def main(base_ref: str) -> int:
    changed = _run("git", "diff", "--name-only", f"{base_ref}...HEAD").splitlines()
    relevant = [path for path in changed if path.startswith(PACKAGED_PATHS)]

    head_cfg = open("setup.cfg").read()
    head_version = _version_from(head_cfg, "metadata", "version")

    # Always enforced, whatever changed: bumpversion does a literal search for its own current_version,
    # so any disagreement here means `make release` is already broken.
    bump_version = _version_from(open(".bumpversion.cfg").read(), "bumpversion", "current_version")
    if bump_version != head_version:
        print(f"::error::setup.cfg says {head_version} but .bumpversion.cfg says {bump_version}.")
        print("Both must agree or bumpversion cannot find the string it rewrites.")
        return 1

    if not relevant:
        print(f"No packaged code changed ({len(changed)} file(s) touched); no version bump required.")
        return 0

    base_version = _version_from(_run("git", "show", f"{base_ref}:setup.cfg"), "metadata", "version")
    print(f"base={base_version} head={head_version} packaged changes={relevant}")

    if _as_tuple(head_version) <= _as_tuple(base_version):
        print(f"::error::{', '.join(relevant)} changed but the version is still {head_version}.")
        print(f"Bump it above {base_version} with `bumpversion patch|minor|major`.")
        return 1

    existing_tags = _run("git", "tag", "--list", f"v{head_version}")
    if existing_tags:
        print(f"::error::tag v{head_version} already exists, so this version can never be published.")
        return 1

    print(f"Version bumped {base_version} -> {head_version}.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "origin/main"))
