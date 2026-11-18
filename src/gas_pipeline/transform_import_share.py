"""Create a typed Silver copy of the retained EPPO import-share reference CSV."""

import csv
from datetime import date
from decimal import Decimal
import hashlib
import io
from pathlib import Path

import pyarrow as pa

import inspect_source as source
from transform_supply import write_silver_run

OUTPUT_ROOT = source.PROJECT_ROOT / "data/processed/silver/import_share"
RESOURCE_ID = "293c5cb3-d384-4242-a036-5552567ae482"
SOURCE_URL = (
    "https://catalog.eppo.go.th/dataset/b3a14e20-8240-4b3e-9021-f0c88b5225be"
    f"/resource/{RESOURCE_ID}/download/dataset_11_82.csv"
)


def transform_import_share(input_path=source.IMPORT_SHARE_PATH, output_root=OUTPUT_ROOT):
    input_path = Path(input_path)
    inspection = source.inspect_import_share(input_path)
    if inspection["status"] != "PASS":
        raise ValueError(f"Import-share validation failed: {inspection['issues']}")
    content = input_path.read_bytes()
    input_hash = hashlib.sha256(content).hexdigest()
    if input_hash != inspection["actual_sha256"]:
        raise ValueError("Input changed after inspection")

    records = []
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig"), newline=""))
    for number, row in enumerate(reader, 1):
        month = date(int(row["Year"]), source.MONTH_NUMBERS[row["Month"]], 1)
        scope = "outside_scope"
        if month in source.EXPECTED_MONTHS:
            scope = "reporting"
        elif month.year == 2014:
            scope = "support_2014"
        records.append({
            "month_start": month,
            "import_category_code": row["Source"],
            "share_percent": Decimal(row["Share"]),
            "unit": row["UNIT"],
            "scope": scope,
            "reference_checks": "PASS" if scope == "reporting" else "NOT_CHECKED",
            "snapshot_sha256": input_hash,
            "source_record_number": number,
            "raw_year": row["Year"],
            "raw_month": row["Month"],
            "raw_source": row["Source"],
            "raw_share": row["Share"],
            "raw_unit": row["UNIT"],
        })

    schema = pa.schema([
        pa.field("month_start", pa.date32(), nullable=False),
        pa.field("share_percent", pa.decimal128(18, 6), nullable=False),
        pa.field("source_record_number", pa.int64(), nullable=False),
        *[pa.field(name, pa.string(), nullable=False) for name in (
            "import_category_code", "unit", "scope", "reference_checks", "snapshot_sha256",
            "raw_year", "raw_month", "raw_source", "raw_share", "raw_unit",
        )],
    ])
    table = pa.Table.from_pylist(records, schema=schema)
    return write_silver_run(table, input_path, input_hash, output_root, inspection, "import_share", {
        "transform_version": "import_share-silver-v1",
        "transform_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "writer_sha256": hashlib.sha256(Path(write_silver_run.__code__.co_filename).read_bytes()).hexdigest(),
        "source_url": SOURCE_URL,
        "resource_id": RESOURCE_ID,
        "measurement_note": "EPPO reported percentages of total imports.",
        "qualification": "PASS covers category completeness and share totals in 2015–2025. Cross-file reconciliation is tracked separately.",
    })


def main():
    try:
        folder, manifest = transform_import_share()
    except (OSError, ValueError, pa.ArrowException) as error:
        print(f"Silver import-share transformation failed\n{error}")
        return 1
    print("Silver import-share transformation passed")
    print("Rows:", manifest["rows"])
    print("Counts:", manifest["scope_counts"])
    print("Output:", folder)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
