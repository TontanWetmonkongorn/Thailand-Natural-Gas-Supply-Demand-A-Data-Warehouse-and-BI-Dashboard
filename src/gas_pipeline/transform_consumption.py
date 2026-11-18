"""Create a typed Silver copy of the retained EPPO sector consumption CSV."""

import csv
from datetime import date
from decimal import Decimal
import hashlib
import io
from pathlib import Path

import pyarrow as pa

import inspect_source as source
from transform_supply import write_silver_run

OUTPUT_ROOT = source.PROJECT_ROOT / "data/processed/silver/consumption"
RESOURCE_ID = "f69c137e-168c-473c-beb0-2f49a3dc076f"
SOURCE_URL = (
    "https://catalog.eppo.go.th/dataset/26f29bb9-fc1e-4a62-a39d-817188a74810"
    f"/resource/{RESOURCE_ID}/download/dataset_11_22.csv"
)


def transform_consumption(input_path=source.CONSUMPTION_PATH, output_root=OUTPUT_ROOT):
    input_path = Path(input_path)
    inspection = source.inspect_consumption(input_path)
    if inspection["status"] != "PASS":
        raise ValueError(f"Consumption validation failed: {inspection['issues']}")
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
            "sector_code": row["Sector"],
            "quantity_mmscfd": Decimal(row["Quantity"]),
            "unit": row["UNIT"],
            "scope": scope,
            "sector_completeness": "PASS" if scope == "reporting" else "NOT_CHECKED",
            "snapshot_sha256": input_hash,
            "source_record_number": number,
            "raw_year": row["Year"],
            "raw_month": row["Month"],
            "raw_sector": row["Sector"],
            "raw_quantity": row["Quantity"],
            "raw_unit": row["UNIT"],
        })

    schema = pa.schema([
        pa.field("month_start", pa.date32(), nullable=False),
        pa.field("quantity_mmscfd", pa.decimal128(18, 6), nullable=False),
        pa.field("source_record_number", pa.int64(), nullable=False),
        *[pa.field(name, pa.string(), nullable=False) for name in (
            "sector_code", "unit", "scope", "sector_completeness", "snapshot_sha256",
            "raw_year", "raw_month", "raw_sector", "raw_quantity", "raw_unit",
        )],
    ])
    table = pa.Table.from_pylist(records, schema=schema)
    return write_silver_run(table, input_path, input_hash, output_root, inspection, "consumption", {
        "transform_version": "consumption-silver-v1",
        "transform_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "writer_sha256": hashlib.sha256(Path(write_silver_run.__code__.co_filename).read_bytes()).hexdigest(),
        "source_url": SOURCE_URL,
        "resource_id": RESOURCE_ID,
        "measurement_note": "EPPO reported MMSCFD. GSP represents gas separation plant processing.",
        "qualification": "PASS for sector completeness covers the 2015–2025 reporting months. Official value reconciliation and KPI acceptance remain pending.",
    })


def main():
    try:
        folder, manifest = transform_consumption()
    except (OSError, ValueError, pa.ArrowException) as error:
        print(f"Silver consumption transformation failed\n{error}")
        return 1
    print("Silver consumption transformation passed")
    print("Rows:", manifest["rows"])
    print("Counts:", manifest["scope_counts"])
    print("Output:", folder)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
