"""Create the persistent warehouse and its first dimension."""

from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
DATABASE = ROOT / "data/warehouse/thailand_gas.duckdb"
SCHEMA = ROOT / "sql/create_sector_dimension.sql"


def main():
    ddl = SCHEMA.read_text(encoding="utf-8")
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(DATABASE)) as connection:
        connection.execute(ddl)
    print(f"Warehouse schema initialized at {DATABASE}")


if __name__ == "__main__":
    main()
