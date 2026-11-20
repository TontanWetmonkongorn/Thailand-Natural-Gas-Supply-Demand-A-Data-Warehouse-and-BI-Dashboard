"""Create the Gold consumption view for one explicit warehouse load."""

import argparse
from hashlib import sha256
from pathlib import Path

import duckdb

from init_warehouse import ROOT

SQL = ROOT / "sql/create_gold_consumption.sql"


def create_view(database, load_id, silver):
    # Parse the ID as an integer before putting it in the persisted view SQL.
    load_id = int(load_id)
    sql = SQL.read_text(encoding="utf-8").format(load_id=load_id)
    with duckdb.connect(str(database), config={"access_mode": "READ_WRITE"}) as con:
        expected = con.execute("""
            SELECT parquet_sha256
            FROM meta_load
            JOIN meta_snapshot USING (snapshot_id)
            JOIN meta_resource USING (resource_id)
            WHERE load_id = ? AND resource_code = 'E2' AND load_state = 'COMPLETE'
        """, [load_id]).fetchone()
        if expected is None or sha256(silver.read_bytes()).hexdigest() != expected[0]:
            raise ValueError("Select a completed consumption load and its exact Silver Parquet file.")

        con.execute("BEGIN TRANSACTION")
        try:
            con.execute(sql)
            actual_rows = con.execute("""
                SELECT month_start, sector_code, consumption_rate_mmscfd, unit_code
                FROM gold.monthly_sector_consumption
                ORDER BY month_start, sector_code
            """).fetchall()
            silver_rows = con.execute("""
                SELECT month_start, sector_code, quantity_mmscfd, unit
                FROM read_parquet(?) WHERE scope = 'reporting'
                ORDER BY month_start, sector_code
            """, [str(silver)]).fetchall()
            if len(actual_rows) != 528 or actual_rows != silver_rows:
                raise ValueError("Gold rows do not match the 528 expected Silver observations.")
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise
    return actual_rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--load-id", type=int, required=True)
    parser.add_argument("--silver", type=Path, required=True)
    args = parser.parse_args()
    if not args.database.is_file():
        parser.error("The warehouse file does not exist.")
    rows = create_view(args.database, args.load_id, args.silver)
    print(f"Verified {len(rows)} Gold rows against Silver.")
    for month, sector, rate, unit in rows:
        if month.isoformat() == "2025-01-01":
            print(f"{month}  {sector:<12} {rate:.6f} {unit}")


if __name__ == "__main__":
    main()
