"""Command-line interface for point, CSV, and GeoJSON operations."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import TextIO

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

    geojson = subparsers.add_parser("geojson", help="write lookup-equivalent region GeoJSON")
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
    """Run bounded CSV lookup with transactional file output."""

    if args.chunk_size < 1:
        raise CsvInputError("--chunk-size must be positive")
    if args.input != "-" and args.output != "-":
        _reject_csv_path_alias(Path(args.input), Path(args.output))

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
    """Write CSV output atomically, leaving an existing destination unchanged on failure."""

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=output_path.parent,
            prefix=f".{output_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as output_stream:
            temporary_path = Path(output_stream.name)
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
        os.replace(temporary_path, output_path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


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

    File destinations are wrapped transactionally by :func:`_process_csv_to_file`.
    A caller that supplies a streaming output such as stdout can observe rows
    written before a later input error because a stream cannot be rolled back.
    """

    reader = csv.DictReader(input_stream)
    if reader.fieldnames is None:
        raise CsvInputError("CSV input has no header")
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
    writer = csv.DictWriter(output_stream, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()

    engine = get_default_lookup()
    rows: list[dict[str, str]] = []
    row_numbers: list[int] = []
    for row_number, row in enumerate(reader, start=2):
        rows.append(row)
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
