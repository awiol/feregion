"""Verify the built wheel through an isolated installed-package boundary."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path


def run(command: list[str], *, cwd: Path | None = None) -> None:
    """Run a verification command and fail with its complete process status."""

    subprocess.run(command, cwd=cwd, check=True)


def main(argv: list[str] | None = None) -> int:
    """Install a wheel in a temporary venv and exercise Python and CLI APIs."""

    parser = argparse.ArgumentParser()
    parser.add_argument("wheel", type=Path)
    args = parser.parse_args(argv)
    wheel = args.wheel.resolve()
    if not wheel.is_file():
        parser.error(f"wheel does not exist: {wheel}")

    with tempfile.TemporaryDirectory(prefix="feregion-wheel-") as temporary:
        venv = Path(temporary) / "venv"
        run([sys.executable, "-m", "venv", "--system-site-packages", str(venv)])
        python = venv / "bin" / "python"
        pip = venv / "bin" / "pip"
        command = venv / "bin" / "fe-region"
        run([str(pip), "install", "--no-deps", str(wheel)])
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
