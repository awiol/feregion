"""Command-line point and CSV behavior through the public main function."""

import csv
from pathlib import Path

import pytest

from feregion.cli import main


def test_cli_point_prints_number_only_by_default(capsys) -> None:
    """The smallest point command returns only the FE number."""

    status = main(["point", "12", "48"])
    captured = capsys.readouterr()
    assert status == 0
    assert captured.out == "543\n"
    assert captured.err == ""


def test_cli_point_can_print_number_and_name(capsys) -> None:
    """The point command adds the name only when requested."""

    status = main(["point", "12", "48", "--name"])
    captured = capsys.readouterr()
    assert status == 0
    assert captured.out == "543\tGERMANY\n"


def test_cli_csv_adds_numbers_and_optional_names(tmp_path: Path) -> None:
    """CSV mode preserves source fields and appends requested FE fields."""

    source = tmp_path / "input.csv"
    output = tmp_path / "output.csv"
    source.write_text("longitude,latitude,value\n12,48,a\n-60,-30,b\n", encoding="utf-8")
    status = main(["csv", str(source), "-o", str(output), "--include-names", "--chunk-size", "1"])
    assert status == 0
    with output.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert rows == [
        {
            "longitude": "12",
            "latitude": "48",
            "value": "a",
            "fe_number": "543",
            "fe_region": "GERMANY",
        },
        {
            "longitude": "-60",
            "latitude": "-30",
            "value": "b",
            "fe_number": "133",
            "fe_region": "NORTHEASTERN ARGENTINA",
        },
    ]


def test_cli_csv_missing_coordinate_column_returns_error_status(tmp_path: Path, capsys) -> None:
    """Malformed CSV headers fail without a traceback and return status 2."""

    source = tmp_path / "input.csv"
    source.write_text("longitude,value\n12,a\n", encoding="utf-8")
    status = main(["csv", str(source)])
    captured = capsys.readouterr()
    assert status == 2
    assert "missing coordinate columns: latitude" in captured.err


def test_cli_csv_non_numeric_coordinate_returns_error_status(tmp_path: Path, capsys) -> None:
    """A textual CSV coordinate identifies the source row in the CLI error."""

    source = tmp_path / "input.csv"
    source.write_text("longitude,latitude\nnot-a-number,48\n", encoding="utf-8")
    status = main(["csv", str(source)])
    captured = capsys.readouterr()
    assert status == 2
    assert "CSV row 2 has a non-numeric coordinate" in captured.err


def test_cli_point_json_contains_coordinate_number_and_name(capsys) -> None:
    """JSON point output is a complete machine-readable scalar result."""

    import json

    status = main(["point", "12", "48", "--json"])
    captured = capsys.readouterr()
    assert status == 0
    assert json.loads(captured.out) == {
        "longitude": 12.0,
        "latitude": 48.0,
        "number": 543,
        "name": "GERMANY",
    }


def test_cli_csv_rejects_non_positive_chunk_size(tmp_path: Path, capsys) -> None:
    """CSV vectorization requires a positive bounded chunk size."""

    source = tmp_path / "input.csv"
    source.write_text("longitude,latitude\n12,48\n", encoding="utf-8")
    status = main(["csv", str(source), "--chunk-size", "0"])
    captured = capsys.readouterr()
    assert status == 2
    assert "--chunk-size must be positive" in captured.err


def test_cli_csv_header_only_writes_header_without_data_rows(tmp_path: Path) -> None:
    """A valid header-only CSV remains valid and gains the requested output field."""

    source = tmp_path / "input.csv"
    output = tmp_path / "output.csv"
    source.write_text("longitude,latitude\n", encoding="utf-8")
    status = main(["csv", str(source), "-o", str(output)])
    assert status == 0
    assert output.read_text(encoding="utf-8") == "longitude,latitude,fe_number\n"


def test_cli_csv_can_use_stdin_and_stdout(monkeypatch, capsys) -> None:
    """Dash paths support Unix pipeline use without temporary files."""

    import io
    import sys

    monkeypatch.setattr(sys, "stdin", io.StringIO("longitude,latitude\n12,48\n"))
    status = main(["csv", "-"])
    captured = capsys.readouterr()
    assert status == 0
    assert captured.out == "longitude,latitude,fe_number\r\n12,48,543\r\n"


def test_cli_geojson_writes_requested_file(tmp_path: Path) -> None:
    """The GeoJSON subcommand reaches the optional geometry writer boundary."""

    output = tmp_path / "regions.geojson"
    status = main(["geojson", str(output)])
    assert status == 0
    assert output.is_file()
    assert '"FeatureCollection"' in output.read_text(encoding="utf-8")


def test_cli_csv_empty_input_reports_missing_header(tmp_path: Path, capsys) -> None:
    """An empty CSV has no usable schema and returns a stable CLI failure."""

    source = tmp_path / "input.csv"
    source.write_text("", encoding="utf-8")
    status = main(["csv", str(source)])
    captured = capsys.readouterr()
    assert status == 2
    assert "CSV input has no header" in captured.err


def test_cli_csv_rejects_same_input_and_output_path_without_modifying_input(
    tmp_path: Path, capsys
) -> None:
    """A CSV path cannot alias itself because output opening would destroy input."""

    source = tmp_path / "data.csv"
    original = "longitude,latitude\n12,48\n"
    source.write_text(original, encoding="utf-8")

    status = main(["csv", str(source), "-o", str(source)])
    captured = capsys.readouterr()

    assert status == 2
    assert "input and output paths must be different" in captured.err
    assert source.read_text(encoding="utf-8") == original


def test_cli_csv_malformed_header_preserves_existing_output_file(tmp_path: Path, capsys) -> None:
    """Schema failure occurs before atomic replacement of an existing destination."""

    source = tmp_path / "input.csv"
    output = tmp_path / "output.csv"
    source.write_text("longitude,value\n12,a\n", encoding="utf-8")
    output.write_text("keep-me\n", encoding="utf-8")

    status = main(["csv", str(source), "-o", str(output)])
    captured = capsys.readouterr()

    assert status == 2
    assert "missing coordinate columns: latitude" in captured.err
    assert output.read_text(encoding="utf-8") == "keep-me\n"


def test_cli_csv_midstream_failure_preserves_existing_output_file(tmp_path: Path, capsys) -> None:
    """A later bad chunk never commits earlier partial rows to a file destination."""

    source = tmp_path / "input.csv"
    output = tmp_path / "output.csv"
    source.write_text("longitude,latitude\n12,48\nnot-a-number,49\n", encoding="utf-8")
    output.write_text("keep-me\n", encoding="utf-8")

    status = main(["csv", str(source), "-o", str(output), "--chunk-size", "1"])
    captured = capsys.readouterr()

    assert status == 2
    assert "CSV row 3 has a non-numeric coordinate" in captured.err
    assert output.read_text(encoding="utf-8") == "keep-me\n"
    assert list(tmp_path.glob(".output.csv.*.tmp")) == []


def test_cli_csv_stdout_can_contain_partial_rows_after_late_failure(monkeypatch, capsys) -> None:
    """Streaming stdout is explicitly non-atomic when a later row fails."""

    import io
    import sys

    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO("longitude,latitude\n12,48\nnot-a-number,49\n"),
    )
    status = main(["csv", "-", "--chunk-size", "1"])
    captured = capsys.readouterr()

    assert status == 2
    assert captured.out == "longitude,latitude,fe_number\r\n12,48,543\r\n"
    assert "CSV row 3 has a non-numeric coordinate" in captured.err


def test_cli_csv_rejects_identical_number_and_name_output_columns(tmp_path: Path, capsys) -> None:
    """Requested names cannot overwrite the numeric region output."""

    source = tmp_path / "input.csv"
    source.write_text("longitude,latitude\n12,48\n", encoding="utf-8")
    status = main(
        [
            "csv",
            str(source),
            "--include-names",
            "--number-column",
            "region",
            "--name-column",
            "region",
        ]
    )
    captured = capsys.readouterr()

    assert status == 2
    assert "region-number and region-name columns must be different" in captured.err


@pytest.mark.parametrize(
    ("option", "column"),
    [
        pytest.param("--number-column", "longitude", id="number-coordinate"),
        pytest.param("--number-column", "value", id="number-existing"),
        pytest.param("--name-column", "latitude", id="name-coordinate"),
        pytest.param("--name-column", "value", id="name-existing"),
    ],
)
def test_cli_csv_rejects_output_column_collisions(
    tmp_path: Path,
    capsys,
    option: str,
    column: str,
) -> None:
    """CSV output fields never silently replace coordinate or existing fields."""

    source = tmp_path / "input.csv"
    source.write_text("longitude,latitude,value\n12,48,a\n", encoding="utf-8")
    args = ["csv", str(source), option, column]
    if option == "--name-column":
        args.append("--include-names")

    status = main(args)
    captured = capsys.readouterr()

    assert status == 2
    assert "CSV" in captured.err


def test_cli_csv_rejects_duplicate_header_without_publishing_output(
    tmp_path: Path, capsys
) -> None:
    """Duplicate CSV labels are ambiguous and must not silently discard a field."""

    source = tmp_path / "input.csv"
    output = tmp_path / "output.csv"
    source.write_text("longitude,longitude,latitude\n12,13,48\n", encoding="utf-8")

    status = main(["csv", str(source), "-o", str(output)])
    captured = capsys.readouterr()

    assert status == 2
    assert "duplicate fields: longitude" in captured.err
    assert not output.exists()


@pytest.mark.parametrize(
    "row",
    [
        pytest.param("12,48,KEEP-ME", id="surplus-field"),
        pytest.param("12", id="missing-field"),
    ],
)
def test_cli_csv_rejects_row_width_mismatch_without_publishing_output(
    tmp_path: Path,
    capsys,
    row: str,
) -> None:
    """A row whose field count differs from the header fails without data loss."""

    source = tmp_path / "input.csv"
    output = tmp_path / "output.csv"
    source.write_text(f"longitude,latitude\n{row}\n", encoding="utf-8")

    status = main(["csv", str(source), "-o", str(output)])
    captured = capsys.readouterr()

    assert status == 2
    assert "field count does not match the header" in captured.err
    assert not output.exists()


def test_cli_csv_rejects_same_coordinate_selector(tmp_path: Path, capsys) -> None:
    """Longitude and latitude must identify two distinct CSV fields."""

    source = tmp_path / "input.csv"
    source.write_text("coordinate\n12\n", encoding="utf-8")

    status = main(
        [
            "csv",
            str(source),
            "--longitude-column",
            "coordinate",
            "--latitude-column",
            "coordinate",
        ]
    )
    captured = capsys.readouterr()

    assert status == 2
    assert "longitude and latitude columns must be different" in captured.err


def test_cli_csv_preserves_existing_destination_mode(tmp_path: Path) -> None:
    """Atomic replacement preserves permission bits of an existing destination."""

    import stat

    source = tmp_path / "input.csv"
    output = tmp_path / "output.csv"
    source.write_text("longitude,latitude\n12,48\n", encoding="utf-8")
    output.write_text("old\n", encoding="utf-8")
    output.chmod(0o640)

    assert main(["csv", str(source), "-o", str(output)]) == 0
    assert stat.S_IMODE(output.stat().st_mode) == 0o640


def test_cli_csv_new_destination_uses_process_umask(tmp_path: Path) -> None:
    """A new published CSV uses normal file-creation permissions under the umask."""

    import os
    import stat

    source = tmp_path / "input.csv"
    output = tmp_path / "output.csv"
    source.write_text("longitude,latitude\n12,48\n", encoding="utf-8")

    previous_umask = os.umask(0o022)
    try:
        assert main(["csv", str(source), "-o", str(output)]) == 0
    finally:
        os.umask(previous_umask)

    assert stat.S_IMODE(output.stat().st_mode) == 0o644


def test_cli_csv_invalid_utf8_returns_bounded_error_without_traceback(
    tmp_path: Path, capsys
) -> None:
    """Invalid UTF-8 input returns the CSV failure status and diagnostic.

    The command owns the text-decoding contract for filesystem CSV input. A
    decoding failure must not escape as ``UnicodeDecodeError`` or publish a
    filesystem destination.
    """

    source = tmp_path / "input.csv"
    output = tmp_path / "output.csv"
    source.write_bytes(b"longitude,latitude\n12,\xff\n")

    status = main(["csv", str(source), "-o", str(output)])
    captured = capsys.readouterr()

    assert status == 2
    assert captured.out == ""
    assert "CSV input must be valid UTF-8" in captured.err
    assert "Traceback" not in captured.err
    assert not output.exists()


def test_cli_csv_malformed_quoting_returns_csv_error_without_publishing(
    tmp_path: Path, capsys
) -> None:
    """Malformed CSV syntax is reported through the package CSV boundary.

    Strict CSV parsing detects an unterminated quoted field. A file destination
    must not be published after the parse failure.
    """

    source = tmp_path / "input.csv"
    output = tmp_path / "output.csv"
    source.write_text('longitude,latitude\n"12,48\n', encoding="utf-8")

    status = main(["csv", str(source), "-o", str(output)])
    captured = capsys.readouterr()

    assert status == 2
    assert "CSV input is malformed:" in captured.err
    assert not output.exists()
