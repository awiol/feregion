"""Command-line interface for point, CSV, and GeoJSON operations."""

from __future__ import annotations

import argparse
import csv
import json
import os
import secrets
import stat
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import TextIO, cast

import numpy as np

from . import lookup_number, number_to_name
from ._default import get_default_lookup
from .exceptions import CsvInputError, FlinnEngdahlError


def build_parser() -> argparse.ArgumentParser:
    """Build the public command parser."""

    parser = argparse.ArgumentParser(prog="fe-region")
    subparsers = parser.add_subparsers(dest="command", required=True)

    point = subparsers.add_parser("point", help="lookup one longitude/latitude pair")
    point.add_argument("longitude", type=float)
    point.add_argument("latitude", type=float)
    point.add_argument("--name", action="store_true", help="also print the region name")
    point.add_argument("--json", action="store_true", help="write one JSON object")

    csv_parser = subparsers.add_parser("csv", help="add region data to a CSV file")
    csv_parser.add_argument("input", help="input CSV path, or '-' for stdin")
    csv_parser.add_argument(
        "-o",
        "--output",
        default="-",
        help="output CSV path, or '-' for stdout",
    )
    csv_parser.add_argument("--longitude-column", default="longitude")
    csv_parser.add_argument("--latitude-column", default="latitude")
    csv_parser.add_argument("--number-column", default="fe_number")
    csv_parser.add_argument("--include-names", action="store_true")
    csv_parser.add_argument("--name-column", default="fe_region")
    csv_parser.add_argument("--chunk-size", type=int, default=100_000)

    geojson = subparsers.add_parser("geojson", help="write derived one-degree region GeoJSON")
    geojson.add_argument("output")
    geojson.add_argument("--indent", type=int, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the command-line interface and return its process exit status."""

    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "point":
            return _point(args)
        if args.command == "csv":
            return _csv(args)
        if args.command == "geojson":
            return _geojson(args)
    except (FlinnEngdahlError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    parser.error("unknown command")  # pragma: no cover -- argparse restricts choices
    return 2  # pragma: no cover -- parser.error always raises


def _point(args: argparse.Namespace) -> int:
    number = lookup_number(args.longitude, args.latitude)
    name = number_to_name(number) if args.name or args.json else None
    if args.json:
        print(
            json.dumps(
                {
                    "longitude": args.longitude,
                    "latitude": args.latitude,
                    "number": number,
                    "name": name,
                },
                ensure_ascii=False,
            )
        )
    elif args.name:
        print(f"{number}\t{name}")
    else:
        print(number)
    return 0


def _csv(args: argparse.Namespace) -> int:
    """Run bounded CSV lookup with atomic filesystem publication."""

    if args.chunk_size < 1:
        raise CsvInputError("--chunk-size must be positive")
    if args.input != "-" and args.output != "-":
        _reject_csv_path_alias(Path(args.input), Path(args.output))

    try:
        with _csv_input(args.input) as input_stream:
            if args.output == "-":
                _process_csv(
                    input_stream,
                    sys.stdout,
                    longitude_column=args.longitude_column,
                    latitude_column=args.latitude_column,
                    number_column=args.number_column,
                    include_names=args.include_names,
                    name_column=args.name_column,
                    chunk_size=args.chunk_size,
                )
            else:
                _process_csv_to_file(
                    input_stream,
                    Path(args.output),
                    longitude_column=args.longitude_column,
                    latitude_column=args.latitude_column,
                    number_column=args.number_column,
                    include_names=args.include_names,
                    name_column=args.name_column,
                    chunk_size=args.chunk_size,
                )
    except UnicodeError as exc:
        raise CsvInputError("CSV input must be valid UTF-8") from exc
    except csv.Error as exc:
        raise CsvInputError(f"CSV input is malformed: {exc}") from exc
    return 0


@contextmanager
def _csv_input(path: str):
    """Yield stdin or a managed UTF-8 CSV input stream."""

    if path == "-":
        yield sys.stdin
        return
    with Path(path).open("r", encoding="utf-8", newline="") as input_stream:
        yield input_stream


def _reject_csv_path_alias(input_path: Path, output_path: Path) -> None:
    """Reject paths that identify the same filesystem entry or resolved path."""

    try:
        if (
            input_path.exists()
            and output_path.exists()
            and os.path.samefile(input_path, output_path)
        ):
            raise CsvInputError("CSV input and output paths must be different")
    except OSError:
        # Resolution below still catches the common lexical/symlink path case.
        pass

    try:
        same_resolved_path = input_path.resolve(strict=False) == output_path.resolve(strict=False)
    except OSError:
        same_resolved_path = os.path.abspath(input_path) == os.path.abspath(output_path)
    if same_resolved_path:
        raise CsvInputError("CSV input and output paths must be different")


def _process_csv_to_file(
    input_stream: TextIO,
    output_path: Path,
    *,
    longitude_column: str,
    latitude_column: str,
    number_column: str,
    include_names: bool,
    name_column: str,
    chunk_size: int,
) -> None:
    """Publish a CSV file atomically after complete successful processing.

    If the destination already exists, preserve its permission bits. If the
    destination is new, create the temporary sibling with normal file-creation
    permissions so the process umask determines the resulting mode.
    """

    temporary_path: Path | None = None
    destination_mode = (
        stat.S_IMODE(output_path.stat().st_mode) if output_path.exists() else None
    )
    try:
        temporary_path, output_stream = _open_csv_temporary(output_path)
        with output_stream:
            _process_csv(
                input_stream,
                output_stream,
                longitude_column=longitude_column,
                latitude_column=latitude_column,
                number_column=number_column,
                include_names=include_names,
                name_column=name_column,
                chunk_size=chunk_size,
            )
        if destination_mode is not None:
            os.chmod(temporary_path, destination_mode)
        os.replace(temporary_path, output_path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _open_csv_temporary(output_path: Path) -> tuple[Path, TextIO]:
    """Create an exclusive temporary sibling using normal umask semantics."""

    for _ in range(100):
        temporary_path = output_path.parent / (
            f".{output_path.name}.{secrets.token_hex(8)}.tmp"
        )
        try:
            descriptor = os.open(
                temporary_path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o666,
            )
        except FileExistsError:
            continue
        return temporary_path, os.fdopen(
            descriptor,
            mode="w",
            encoding="utf-8",
            newline="",
        )
    raise OSError(f"cannot create temporary CSV sibling for {output_path}")


def _process_csv(
    input_stream: TextIO,
    output_stream: TextIO,
    *,
    longitude_column: str,
    latitude_column: str,
    number_column: str,
    include_names: bool,
    name_column: str,
    chunk_size: int,
) -> None:
    """Process CSV records in bounded vectorized chunks.

    File destinations use atomic publication through :func:`_process_csv_to_file`.
    A caller that supplies a streaming output such as stdout can observe rows
    written before a later input error because a stream cannot be rolled back.
    """

    reader = csv.DictReader(input_stream, strict=True)
    if reader.fieldnames is None:
        raise CsvInputError("CSV input has no header")
    duplicate_headers = _duplicate_csv_headers(reader.fieldnames)
    if duplicate_headers:
        raise CsvInputError(
            "CSV header contains duplicate fields: " + ", ".join(duplicate_headers)
        )
    if longitude_column == latitude_column:
        raise CsvInputError("CSV longitude and latitude columns must be different")
    missing = [
        column for column in (longitude_column, latitude_column) if column not in reader.fieldnames
    ]
    if missing:
        raise CsvInputError(f"CSV is missing coordinate columns: {', '.join(missing)}")

    _validate_csv_output_columns(
        reader.fieldnames,
        longitude_column=longitude_column,
        latitude_column=latitude_column,
        number_column=number_column,
        include_names=include_names,
        name_column=name_column,
    )

    fieldnames = [*reader.fieldnames, number_column]
    if include_names:
        fieldnames.append(name_column)
    writer = csv.DictWriter(output_stream, fieldnames=fieldnames, extrasaction="raise")
    writer.writeheader()

    engine = get_default_lookup()
    rows: list[dict[str, str]] = []
    row_numbers: list[int] = []
    for row_number, row in enumerate(reader, start=2):
        _validate_csv_row_width(row, row_number)
        rows.append(cast(dict[str, str], row))
        row_numbers.append(row_number)
        if len(rows) >= chunk_size:
            _write_csv_chunk(
                rows,
                row_numbers,
                writer,
                engine=engine,
                longitude_column=longitude_column,
                latitude_column=latitude_column,
                number_column=number_column,
                include_names=include_names,
                name_column=name_column,
            )
            rows = []
            row_numbers = []
    if rows:
        _write_csv_chunk(
            rows,
            row_numbers,
            writer,
            engine=engine,
            longitude_column=longitude_column,
            latitude_column=latitude_column,
            number_column=number_column,
            include_names=include_names,
            name_column=name_column,
        )


def _duplicate_csv_headers(fieldnames: list[str]) -> list[str]:
    """Return duplicate header labels in first-repeat order."""

    seen: set[str] = set()
    duplicates: list[str] = []
    for fieldname in fieldnames:
        if fieldname in seen and fieldname not in duplicates:
            duplicates.append(fieldname)
        seen.add(fieldname)
    return duplicates


def _validate_csv_row_width(row: dict[str | None, str | list[str] | None], row_number: int) -> None:
    """Reject rows whose field count differs from the declared header width."""

    if None in row or any(value is None for value in row.values()):
        raise CsvInputError(
            f"CSV row {row_number} field count does not match the header"
        )


def _validate_csv_output_columns(
    fieldnames: list[str],
    *,
    longitude_column: str,
    latitude_column: str,
    number_column: str,
    include_names: bool,
    name_column: str,
) -> None:
    """Reject output schemas that would overwrite or collapse input fields."""

    coordinate_columns = {longitude_column, latitude_column}
    if number_column in coordinate_columns:
        raise CsvInputError("CSV region-number column must differ from coordinate columns")
    if number_column in fieldnames:
        raise CsvInputError(f"CSV output column already exists: {number_column}")

    if not include_names:
        return
    if name_column == number_column:
        raise CsvInputError("CSV region-number and region-name columns must be different")
    if name_column in coordinate_columns:
        raise CsvInputError("CSV region-name column must differ from coordinate columns")
    if name_column in fieldnames:
        raise CsvInputError(f"CSV output column already exists: {name_column}")


def _write_csv_chunk(
    rows: list[dict[str, str]],
    row_numbers: list[int],
    writer: csv.DictWriter,
    *,
    engine,
    longitude_column: str,
    latitude_column: str,
    number_column: str,
    include_names: bool,
    name_column: str,
) -> None:
    coordinates = np.empty((len(rows), 2), dtype=np.float64)
    for index, (row, row_number) in enumerate(zip(rows, row_numbers, strict=True)):
        try:
            coordinates[index, 0] = float(row[longitude_column])
            coordinates[index, 1] = float(row[latitude_column])
        except (TypeError, ValueError) as exc:
            raise CsvInputError(f"CSV row {row_number} has a non-numeric coordinate") from exc

    numbers = engine.lookup_numbers(coordinates)
    names = engine.numbers_to_names(numbers) if include_names else None
    for index, row in enumerate(rows):
        row[number_column] = str(int(numbers[index]))
        if names is not None:
            row[name_column] = str(names[index])
        writer.writerow(row)


def _geojson(args: argparse.Namespace) -> int:
    from .geojson import write_regions_geojson

    write_regions_geojson(Path(args.output), indent=args.indent)
    return 0
