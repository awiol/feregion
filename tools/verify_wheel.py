"""Verify a built wheel in a dependency-isolated uv virtual environment."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def run(command: list[str], *, cwd: Path | None = None) -> None:
    """Run a verification command and fail with its complete process status."""

    subprocess.run(command, cwd=cwd, check=True)


def main(argv: list[str] | None = None) -> int:
    """Install a wheel with dependencies and exercise Python and CLI APIs."""

    parser = argparse.ArgumentParser()
    parser.add_argument("wheel", type=Path)
    parser.add_argument("--python", default="3.11")
    args = parser.parse_args(argv)
    wheel = args.wheel.resolve()
    if not wheel.is_file():
        parser.error(f"wheel does not exist: {wheel}")

    uv = shutil.which("uv")
    if uv is None:
        parser.error("uv is required for isolated wheel verification")

    with tempfile.TemporaryDirectory(prefix="feregion-wheel-") as temporary:
        venv = Path(temporary) / "venv"
        run([uv, "venv", "--python", args.python, str(venv)])
        scripts = venv / ("Scripts" if os.name == "nt" else "bin")
        python = scripts / ("python.exe" if os.name == "nt" else "python")
        command = scripts / ("fe-region.exe" if os.name == "nt" else "fe-region")
        run([uv, "pip", "install", "--python", str(python), str(wheel)])
        check = (
            "import numpy as np, feregion; "
            "assert feregion.lookup_number(12,48)==543; "
            "assert feregion.lookup_numbers(np.array([[12,48],[-60,-30]])).tolist()==[543,133]; "
            "assert feregion.numbers_to_names(np.array([543,133],dtype=np.uint16)).tolist()=="
            "['GERMANY','NORTHEASTERN ARGENTINA']"
        )
        run([str(python), "-c", check], cwd=Path(temporary))
        run([str(command), "point", "12", "48", "--name"], cwd=Path(temporary))
        run([str(python), "-m", "feregion", "point", "-60", "-30", "--name"], cwd=Path(temporary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
