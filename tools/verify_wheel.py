"""Verify a built wheel before source-bundle delivery or package release."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import tempfile
import zipfile
from email.parser import Parser
from pathlib import Path

REQUIRED_PACKAGE_FILES = {
    "feregion/__init__.py",
    "feregion/__main__.py",
    "feregion/core.py",
    "feregion/cli.py",
    "feregion/pandas.py",
    "feregion/geojson.py",
    "feregion/py.typed",
    "feregion/data/fe_table.npy",
    "feregion/data/fe_names.npy",
    "feregion/data/metadata.json",
}
REQUIRED_EXTRAS = {"pandas", "geo", "test", "benchmark", "dev"}
FORBIDDEN_PREFIXES = ("tests/", "benchmarks/", "tools/")


def run(command: list[str], *, cwd: Path | None = None) -> None:
    """Run one verification command and fail with its complete process status."""

    subprocess.run(command, cwd=cwd, check=True)


def inspect_wheel(wheel: Path, *, expected_version: str | None = None) -> str:
    """Inspect wheel contents and metadata without importing the package.

    Args:
        wheel: Built wheel file to inspect.
        expected_version: Optional exact package version expected in ``METADATA``.

    Returns:
        The package version recorded in wheel metadata.

    Raises:
        ValueError: If required package data, metadata, entry points, license
            notices, or optional-extra declarations are missing, or if
            repository-only source is present in the runtime wheel.
    """

    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
        missing = sorted(REQUIRED_PACKAGE_FILES - names)
        if missing:
            raise ValueError(f"wheel is missing required package files: {missing}")
        forbidden = sorted(name for name in names if name.startswith(FORBIDDEN_PREFIXES))
        if forbidden:
            raise ValueError(f"wheel contains repository-only files: {forbidden}")

        metadata_names = [name for name in names if name.endswith(".dist-info/METADATA")]
        if len(metadata_names) != 1:
            raise ValueError("wheel must contain exactly one dist-info/METADATA file")
        metadata = Parser().parsestr(archive.read(metadata_names[0]).decode("utf-8"))
        version = metadata.get("Version")
        if not version:
            raise ValueError("wheel metadata does not declare Version")
        if expected_version is not None and version != expected_version:
            raise ValueError(f"wheel version mismatch: expected {expected_version}, got {version}")
        if metadata.get("Requires-Python") != ">=3.11":
            raise ValueError("wheel metadata does not preserve Requires-Python >=3.11")
        extras = set(metadata.get_all("Provides-Extra") or [])
        if not REQUIRED_EXTRAS.issubset(extras):
            raise ValueError(
                f"wheel is missing declared optional extras: {sorted(REQUIRED_EXTRAS - extras)}"
            )

        entry_points = [name for name in names if name.endswith(".dist-info/entry_points.txt")]
        if len(entry_points) != 1:
            raise ValueError("wheel must contain exactly one entry_points.txt")
        entry_text = archive.read(entry_points[0]).decode("utf-8")
        if "fe-region = feregion.cli:main" not in entry_text:
            raise ValueError("wheel does not declare the fe-region console script")

        license_suffixes = {
            "licenses/LICENSE",
            "licenses/THIRD_PARTY_NOTICES.md",
            "licenses/LICENSES/GPL-3.0.txt",
        }
        for suffix in license_suffixes:
            if not any(name.endswith(suffix) for name in names):
                raise ValueError(f"wheel is missing license/notice file: {suffix}")
    return version


def main(argv: list[str] | None = None) -> int:
    """Inspect, install, and exercise one wheel in a clean uv environment.

    The command first checks the wheel archive itself. It then creates a new uv
    virtual environment, installs the wheel with dependencies, and exercises
    representative Python and CLI behavior against the installed artifact.
    """

    parser = argparse.ArgumentParser()
    parser.add_argument("wheel", type=Path)
    parser.add_argument("--python", default="3.11")
    parser.add_argument("--expected-version")
    args = parser.parse_args(argv)
    wheel = args.wheel.resolve()
    if not wheel.is_file():
        parser.error(f"wheel does not exist: {wheel}")

    inspect_wheel(wheel, expected_version=args.expected_version)

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
        run(
            [str(python), "-m", "feregion", "point", "-60", "-30", "--name"],
            cwd=Path(temporary),
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
