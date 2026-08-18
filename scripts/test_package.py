from pathlib import (
    Path,
)
import subprocess
from tempfile import (
    TemporaryDirectory,
)
from typing import (
    Tuple,
)


def create_venv(parent_path: Path) -> Path:
    venv_path = parent_path / "package-smoke-test"
    subprocess.run(["uv", "venv", str(venv_path)], check=True)
    return venv_path


def find_wheel(project_path: Path) -> Path:
    wheels = list(project_path.glob("dist/*.whl"))

    if len(wheels) != 1:
        raise Exception(f"Expected one wheel. Instead found: {wheels} " f"in project {project_path.absolute()}")

    return wheels[0]


def install_wheel(venv_path: Path, wheel_path: Path, extras: Tuple[str, ...] = ()) -> None:
    if extras:
        extra_suffix = f"[{','.join(extras)}]"
    else:
        extra_suffix = ""

    subprocess.run(
        [
            "uv",
            "pip",
            "install",
            "--python",
            str(venv_path / "bin" / "python"),
            f"{wheel_path}{extra_suffix}",
        ],
        check=True,
    )


def test_install_local_wheel() -> None:
    with TemporaryDirectory() as tmpdir:
        venv_path = create_venv(Path(tmpdir))
        wheel_path = find_wheel(Path("."))
        install_wheel(venv_path, wheel_path)
        print("Installed", wheel_path.absolute(), "to", venv_path)
        print(f"Activate with `source {venv_path}/bin/activate`")
        input("Press enter when the test has completed. The directory will be deleted.")


if __name__ == "__main__":
    test_install_local_wheel()
