"""Create the Gold supply source view for one explicit warehouse load."""

import argparse
from hashlib import sha256
from pathlib import Path

import duckdb

from init_warehouse import ROOT

SQL = ROOT / "sql/create_gold_supply.sql"


def create_view(database, load_id, silver):
    load_id = int(load_id)
    sql = SQL.read_text(encoding="utf-8").format(load_id=load_id)
    with duckdb.connect(str(database), config={"access_mode": "READ_WRITE"}) as con:
        expected = con.execute("""
            SELECT parquet_sha256
            FROM meta_load
            JOIN meta_snapshot USING (snapshot_id)
            JOIN meta_resource USING (resource_id)
            WHERE load_id = ? AND resource_code = 'E1' AND load_state = 'COMPLETE'
        """, [load_id]).fetchone()
        if expected is None or sha256(silver.read_bytes()).hexdigest() != expected[0]:
            raise ValueError("Select a completed supply load and its exact Silver Parquet file.")

        con.execute("BEGIN TRANSACTION")
        try:
            con.execute(sql)
            actual = con.execute("""
                SELECT month_start, source_code, supply_rate_mmscfd, unit_code,
                       source_completeness, import_mix_status
                FROM gold.monthly_supply_by_source
                ORDER BY month_start, source_code
            """).fetchall()
            reference = con.execute("""
                SELECT month_start, source_code, quantity_mmscfd, unit,
                       source_completeness, import_mix_status
                FROM read_parquet(?) WHERE scope = 'reporting'
                ORDER BY month_start, source_code
            """, [str(silver)]).fetchall()
            if len(actual) != 2277 or actual != reference:
                raise ValueError("Gold rows or review flags differ from the 2,277 Silver observations.")
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise
    return len(actual)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--load-id", type=int, required=True)
    parser.add_argument("--silver", type=Path, required=True)
    args = parser.parse_args()
    if not args.database.is_file():
        parser.error("The warehouse file does not exist.")
    count = create_view(args.database, args.load_id, args.silver)
    print(f"Verified {count:,} Gold supply rows and flags against Silver.")


if __name__ == "__main__":
    main()
