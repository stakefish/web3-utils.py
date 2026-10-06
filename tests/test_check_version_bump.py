import subprocess
import sys
from pathlib import Path

import pytest

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
