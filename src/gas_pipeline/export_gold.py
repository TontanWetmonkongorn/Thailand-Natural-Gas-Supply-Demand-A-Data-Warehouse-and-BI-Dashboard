"""Export a consistent set of Gold views for Power BI."""

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

import duckdb

from init_warehouse import ROOT

# View names and ordering are fixed here. Only the destination is supplied at runtime.
EXPORTS = (
    ("monthly_sector_consumption", "month_start, sector_code", 528),
    ("monthly_consumption_totals", "month_start", 132),
    ("monthly_consumption_sector_shares", "month_start, sector_code", 528),
    ("monthly_supply_by_source", "month_start, source_code", 2277),
    ("monthly_published_import_mix", "month_start, category_code", 264),
)


def export_gold(database, output_root):
    output_root.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    destination = output_root / f"{now:%Y%m%dT%H%M%SZ}_{uuid4().hex[:12]}"
    manifest = {"exported_at_utc": now.isoformat(), "database": database.name, "files": {}}
    with TemporaryDirectory(dir=output_root) as temporary:
        staging = Path(temporary) / "export"
        staging.mkdir()
        with duckdb.connect(str(database), read_only=True) as con:
            con.execute("BEGIN TRANSACTION")
            for view, order, expected_rows in EXPORTS:
                view_name = f"gold.{view}"
                rows, loads = con.execute(
                    f"SELECT count(*), list(DISTINCT load_id ORDER BY load_id) FROM {view_name}"
                ).fetchone()
                if rows != expected_rows or len(loads) != 1:
                    raise ValueError(f"{view_name} must contain {expected_rows} rows from one load.")
                csv_path = staging / f"{view}.csv"
                con.execute(
                    f"COPY (SELECT * FROM {view_name} ORDER BY {order}) TO ? (FORMAT CSV, HEADER)",
                    [str(csv_path)],
                )
                manifest["files"][csv_path.name] = {
                    "rows": rows,
                    "load_id": loads[0],
                    "sha256": sha256(csv_path.read_bytes()).hexdigest(),
                }
            con.execute("COMMIT")
        (staging / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        staging.rename(destination)
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=ROOT / "outputs/power_bi")
    args = parser.parse_args()
    if not args.database.is_file():
        parser.error("The warehouse file does not exist.")
    print(export_gold(args.database, args.output_root))


if __name__ == "__main__":
    main()
