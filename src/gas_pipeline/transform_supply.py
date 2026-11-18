"""Create a traceable, typed Silver copy of the retained EPPO supply CSV."""

import csv
from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import io
import json
from pathlib import Path
import tempfile
from uuid import uuid4

import pyarrow as pa
import pyarrow.parquet as pq

import compare_import_share
import inspect_source as source

OUTPUT_ROOT = source.PROJECT_ROOT / "data/processed/silver/supply"
SOURCE_URL = "https://catalog.eppo.go.th/dataset/799ad6f1-db30-4910-8d21-7ec670a7ba89/resource/7a74d96f-d988-4588-b1d1-8e7824c0d08c/download/dataset_11_20.csv"
TRANSFORM_VERSION = "supply-silver-v1"


def build_table(content, input_hash, import_mix_status):
    """Called only after input validation. Preserve every original CSV record."""
    records = []
    for number, row in enumerate(csv.DictReader(io.StringIO(content.decode("utf-8-sig"))), 1):
        month = date(int(row["Year"]), source.MONTH_NUMBERS[row["Month"]], 1)
        scope = "reporting" if month in source.EXPECTED_MONTHS else "support_2014" if month.year == 2014 else "outside_scope"
        records.append({
            "month_start": month,
            "source_code": row["Source"],
            "quantity_mmscfd": Decimal(row["Quantity"]),
            "unit": row["UNIT"],
            "scope": scope,
            "source_completeness": "UNRESOLVED",
            "import_mix_status": import_mix_status.get(month.isoformat()[:7], "NOT_CHECKED"),
            "snapshot_sha256": input_hash,
            "source_record_number": number,
            "raw_year": row["Year"], "raw_month": row["Month"],
            "raw_source": row["Source"], "raw_quantity": row["Quantity"], "raw_unit": row["UNIT"],
        })
    schema = pa.schema([
        pa.field("month_start", pa.date32(), nullable=False),
        pa.field("source_code", pa.string(), nullable=False),
        pa.field("quantity_mmscfd", pa.decimal128(18, 6), nullable=False),
        *[pa.field(name, pa.string(), nullable=False) for name in
          ("unit", "scope", "source_completeness", "import_mix_status", "snapshot_sha256")],
        pa.field("source_record_number", pa.int64(), nullable=False),
        *[pa.field(name, pa.string(), nullable=False) for name in
          ("raw_year", "raw_month", "raw_source", "raw_quantity", "raw_unit")],
    ])
    return pa.Table.from_pylist(records, schema=schema)


def transform_supply(input_path=source.INPUT_PATH, output_root=OUTPUT_ROOT):
    input_path = Path(input_path)
    inspection = source.inspect_supply(input_path)
    if inspection["status"] != "PASS":
        raise ValueError(f"Supply validation failed; no Silver output written: {inspection['issues']}")
    content = input_path.read_bytes()
    input_hash = hashlib.sha256(content).hexdigest()
    if input_hash != inspection["actual_sha256"]:
        raise ValueError("Input changed after inspection; no Silver output written")
    # Recompute rather than trusting an old report. This does not apply the April supplement.
    comparison = compare_import_share.run_comparison()
    statuses = {row["month"]: row["status"] for row in comparison["months"]}
    table = build_table(content, input_hash, statuses)
    return write_silver_run(table, input_path, input_hash, output_root, inspection, "supply", {
        "transform_version": TRANSFORM_VERSION,
        "transform_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "source_url": SOURCE_URL,
        "resource_id": "7a74d96f-d988-4588-b1d1-8e7824c0d08c",
        "measurement_note": "EPPO reported MMSCFD; Myanmar gas heat-value basis 1,000 BTU/SCF; no unit conversion",
        "import_mix_comparison": comparison,
        "qualification": "Typed source observations, not publication-ready KPI data. National source completeness unresolved. April workbook supplement not applied.",
    })


def write_silver_run(table, input_path, input_hash, output_root, inspection, dataset, metadata):
    """Verify and publish the Parquet file and manifest together."""
    if table.num_rows != inspection["summary"]["validated_records"]:
        raise ValueError("Silver row count differs from inspected input")
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid4().hex[:12]
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    final_dir = output_root / run_id
    # A failed write never leaves a finished run directory or overwrites an earlier run.
    with tempfile.TemporaryDirectory(prefix=".building_", dir=output_root) as temporary:
        staging = Path(temporary) / "run"
        staging.mkdir()
        parquet_path = staging / f"{dataset}.parquet"
        pq.write_table(table, parquet_path)
        restored = pq.read_table(parquet_path)
        if not restored.equals(table):
            raise ValueError("Parquet round trip changed table values/types")
        if hashlib.sha256(input_path.read_bytes()).hexdigest() != input_hash:
            raise ValueError("Input changed during transformation")
        manifest = {
            "run_id": run_id, "processed_at_utc": datetime.now(timezone.utc).isoformat(),
            **metadata,
            "input_path": str(input_path.resolve()), "input_sha256": input_hash,
            "input_retrieved_at_utc": None,
            "output_file": parquet_path.name,
            "output_sha256": hashlib.sha256(parquet_path.read_bytes()).hexdigest(),
            "rows": table.num_rows, "schema": str(table.schema),
            "scope_counts": inspection["summary"]["scope_counts"],
            "inspection": inspection,
            "inputs_unchanged": True, "parquet_round_trip": "PASS",
        }
        (staging / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        staging.rename(final_dir)
    return final_dir, manifest


def main():
    try:
        folder, manifest = transform_supply()
    except (OSError, ValueError, pa.ArrowException) as error:
        print(f"Silver supply transformation: FAIL\n{error}")
        return 1
    print("Silver supply transformation: PASS")
    print("Rows:", manifest["rows"])
    print("Counts:", manifest["scope_counts"])
    print("Output:", folder)
    print("Import-mix comparison:", manifest["import_mix_comparison"]["status"])
    print(manifest["qualification"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
