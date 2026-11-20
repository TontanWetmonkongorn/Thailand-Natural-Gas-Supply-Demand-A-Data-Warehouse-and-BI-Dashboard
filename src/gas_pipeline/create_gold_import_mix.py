"""Create the Gold published import mix view for one explicit warehouse load."""

import argparse
from hashlib import sha256
from pathlib import Path

import duckdb

from init_warehouse import ROOT

SQL = ROOT / "sql/create_gold_import_mix.sql"


def create_view(database, load_id, silver):
    load_id = int(load_id)
    sql = SQL.read_text(encoding="utf-8").format(load_id=load_id)
    with duckdb.connect(str(database), config={"access_mode": "READ_WRITE"}) as con:
        expected = con.execute("""
            SELECT parquet_sha256
            FROM meta_load
            JOIN meta_snapshot USING (snapshot_id)
            JOIN meta_resource USING (resource_id)
            WHERE load_id = ? AND resource_code = 'E3' AND load_state = 'COMPLETE'
        """, [load_id]).fetchone()
        if expected is None or sha256(silver.read_bytes()).hexdigest() != expected[0]:
            raise ValueError("Select a completed import-share load and its exact Silver Parquet file.")

        con.execute("BEGIN TRANSACTION")
        try:
            con.execute(sql)
            actual = con.execute("""
                SELECT month_start, category_code, import_share_pct, unit_code
                FROM gold.monthly_published_import_mix
                ORDER BY month_start, category_code
            """).fetchall()
            reference = con.execute("""
                SELECT month_start, import_category_code, share_percent, unit
                FROM read_parquet(?) WHERE scope = 'reporting'
                ORDER BY month_start, import_category_code
            """, [str(silver)]).fetchall()
            if len(actual) != 264 or actual != reference:
                raise ValueError("Gold rows differ from the 264 Silver import-share observations.")
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
    print(f"Verified {count:,} Gold published import-share rows against Silver.")


if __name__ == "__main__":
    main()
