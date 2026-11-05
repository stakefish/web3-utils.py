import subprocess
import sys
from pathlib import Path

import pytest
from packaging.version import Version

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_version_bump.py"


def git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()


def write_version(repo, version):
    (repo / "setup.cfg").write_text(f"[metadata]\nversion = {version}\n")
    (repo / ".bumpversion.cfg").write_text(f"[bumpversion]\ncurrent_version = {version}\n")


@pytest.fixture
def version_repo(tmp_path):
    git(tmp_path, "init")
    git(tmp_path, "config", "user.name", "Version gate test")
    git(tmp_path, "config", "user.email", "version-test@example.invalid")
    git(tmp_path, "config", "commit.gpgSign", "false")
    (tmp_path / "web3_utils").mkdir()
    return tmp_path


@pytest.mark.parametrize(
    "base_version,head_version,expected_code",
    [
        ("0.12.0b.1", "0.12.0rc.1", 0),
        ("0.12.0rc.1", "0.12.0", 0),
        ("0.12.0b.99", "0.12.1", 0),
        ("0.12.3", "0.12.4", 0),
        ("0.12.3", "0.12.0b.4", 1),
        ("0.12.3", "0.12.2", 1),
        ("0.12.3", "0.12.3", 1),
        ("0.12.0b.1", "0.12.0b1", 1),
        ("0.12.3", "not-a-version", 1),
        ("not-a-version", "0.12.4", 1),
    ],
)
def test_version_gate(version_repo, base_version, head_version, expected_code):
    write_version(version_repo, base_version)
    package_file = version_repo / "web3_utils" / "__init__.py"
    package_file.write_text("# base\n")
    git(version_repo, "add", ".")
    git(version_repo, "commit", "-m", "Base version")
    base_ref = git(version_repo, "rev-parse", "HEAD")

    write_version(version_repo, head_version)
    package_file.write_text("# changed\n")
    git(version_repo, "add", ".")
    git(version_repo, "commit", "-m", "Changed package")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), base_ref],
        cwd=version_repo,
        capture_output=True,
        text=True,
    )

    assert result.returncode == expected_code, result.stdout + result.stderr
    assert "Traceback" not in result.stderr
    if "not-a-version" in (base_version, head_version):
        assert "::error::Invalid release version" in result.stdout


@pytest.mark.parametrize(
    "current_version,part,expected_version",
    [
        ("0.12.5rc.1", "stage", "0.12.5"),
        ("0.12.5b.2", "stage", "0.12.5rc.0"),
        ("0.12.5rc.1", "devnum", "0.12.5rc.2"),
        ("0.12.5rc.1", "patch", "0.12.6"),
        ("0.12.4", "patch", "0.12.5"),
        ("0.12.4", "minor", "0.13.0"),
    ],
)
def test_bumpversion_config_produces_pep440_versions(current_version, part, expected_version):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "bumpversion",
            "--dry-run",
            "--verbose",
            "--allow-dirty",
            "--no-commit",
            "--no-tag",
            "--current-version",
            current_version,
            part,
            "setup.cfg",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )

    assert f"New version will be '{expected_version}'" in result.stdout + result.stderr, result.stdout + result.stderr
    Version(expected_version)
