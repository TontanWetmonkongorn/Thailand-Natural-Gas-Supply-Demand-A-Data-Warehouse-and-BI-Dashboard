"""Load explicit Silver runs into the local DuckDB warehouse in one transaction."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

import duckdb

import inspect_source as source
from init_warehouse import DATABASE, ROOT, SCHEMA

# Order matches the command-line arguments and the independent fact tables.
DATASETS = (
    ("supply", source.EXPECTED_HASH, "E1", "fact_gas_supply_monthly",
     "gas_source", "source_code", "source_code", "quantity_mmscfd", 2461, 3),
    ("consumption", source.CONSUMPTION_HASH, "E2", "fact_gas_consumption_monthly",
     "sector", "sector_code", "sector_code", "quantity_mmscfd", 576, 1),
    ("import_share", source.IMPORT_SHARE_HASH, "E3", "fact_import_share_monthly",
     "import_category", "category_code", "import_category_code", "share_percent", 288, 2),
)


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def ensure_row(con, table, key_columns, row):
    """Reuse identical existing rows. Refuse to silently replace manual entries."""
    columns = list(row)
    where = " AND ".join(f"{column} = ?" for column in key_columns)
    keys = [row[column] for column in key_columns]
    previous = con.execute(f"SELECT {', '.join(columns)} FROM {table} WHERE {where}", keys).fetchone()
    values = tuple(row.values())
    if previous is None:
        placeholders = ", ".join("?" for _ in values)
        con.execute(f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})", values)
    elif previous != values:
        raise ValueError(f"Existing {table} row differs from the selected definition: {keys}")


def load_dimensions(con):
    for version, filename in enumerate(("sector", "import_category", "gas_source"), 1):
        path = Path(f"config/{filename}_definitions_v1.json")
        content = (ROOT / path).read_bytes()
        manifest = json.loads(content)
        ensure_row(con, "meta_definition_version", ["definition_version_id"], {
            "definition_version_id": version,
            "version_label": manifest["version_label"],
            "manifest_path": path.as_posix(),
            "manifest_sha256": sha256(content).hexdigest(),
            "evidence_references": "docs/source_assessment.md",
            "review_state": manifest["review_state"],
        })
        if filename == "sector":
            rows = [{"sector_code": item["code"], "sector_name": item["name"],
                     "definition_note": item.get("note")} for item in manifest["sectors"]]
            code = "sector_code"
        elif filename == "import_category":
            rows = [{"category_code": item["code"], "category_name": item["name"],
                     "denominator_description": item["denominator_description"]}
                    for item in manifest["categories"]]
            code = "category_code"
        else:
            rows = [{"source_code": label, "source_name": label, "supply_group": group,
                     "qualification_note": manifest["notes"].get(label)}
                    for group, labels in manifest["groups"].items() for label in labels]
            code = "source_code"
        expected_codes = (source.ALLOWED_SECTORS, source.IMPORT_CATEGORIES, source.ALLOWED_SOURCES)[version - 1]
        if len(rows) != len(expected_codes) or {row[code] for row in rows} != expected_codes:
            raise ValueError(f"Incorrect category codes in {path}")
        for row in rows:
            ensure_row(con, f"dim_{filename}", [code, "definition_version_id"],
                       {**row, "definition_version_id": version})

    for code, name, kind in (("MMSCFD", "Million standard cubic feet per day", "RATE"),
                             ("%", "Percent", "PERCENTAGE")):
        ensure_row(con, "dim_unit", ["unit_code"], dict(unit_code=code, unit_name=name, measure_kind=kind))
    con.execute("""
        INSERT INTO dim_month
        SELECT CAST(m AS DATE), year(m), month(m), strftime(m, '%B'), day(last_day(m))
        FROM generate_series(DATE '2014-01-01', DATE '2025-12-01', INTERVAL '1 month') AS calendar(m)
        WHERE NOT EXISTS (SELECT 1 FROM dim_month WHERE month_start = CAST(m AS DATE))
    """)


def load_fact(con, spec, folder):
    name, expected_hash, resource, fact, dimension, code, incoming_code, value, expected_count, version = spec
    manifest = json.loads((folder / "manifest.json").read_bytes())
    parquet = folder / f"{name}.parquet"
    parquet_hash = digest(parquet)
    inspection = manifest["inspection"]
    if (manifest["input_sha256"] != expected_hash or inspection["actual_sha256"] != expected_hash
            or inspection["status"] != "PASS" or parquet_hash != manifest["output_sha256"]
            or manifest["output_file"] != parquet.name or manifest["parquet_round_trip"] != "PASS"):
        raise ValueError(f"Invalid Silver manifest or fingerprint for {name}")

    ensure_row(con, "meta_resource", ["resource_code"], {
        "resource_code": resource, "publisher_name": "EPPO",
        "publisher_resource_id": manifest["resource_id"], "download_url": manifest["source_url"],
    })
    resource_id, = con.execute("SELECT resource_id FROM meta_resource WHERE resource_code = ?", [resource]).fetchone()
    con.execute("""
        INSERT INTO meta_snapshot (resource_id, sha256, raw_path, download_url_at_retrieval, retrieved_at)
        VALUES (?, ?, ?, ?, ?) ON CONFLICT (resource_id, sha256) DO NOTHING
    """, [resource_id, expected_hash, manifest["input_path"], manifest["source_url"], manifest["input_retrieved_at_utc"]])
    snapshot_id, = con.execute("SELECT snapshot_id FROM meta_snapshot WHERE resource_id = ? AND sha256 = ?",
                               [resource_id, expected_hash]).fetchone()
    transform = ":".join([manifest["transform_version"], manifest["transform_sha256"],
                          manifest.get("writer_sha256", ""), digest(Path(__file__)),
                          digest(ROOT / "sql/create_warehouse.sql")])
    rules = inspection["rule_version"] + ":" + inspection["checker_sha256"]
    identity = [snapshot_id, version, transform, rules, digest(ROOT / "config/warehouse_resolutions_v1.json")]
    identity_filter = """
        snapshot_id = ? AND definition_version_id = ? AND transform_version = ?
        AND ruleset_version = ? AND resolution_manifest_sha256 = ?
    """
    existing = con.execute(f"SELECT load_id, parquet_sha256 FROM meta_load WHERE {identity_filter}", identity).fetchone()
    if existing:
        load_id, saved_hash = existing
        if saved_hash != parquet_hash:
            raise ValueError(f"Existing {name} interpretation has a different Parquet fingerprint")
    else:
        load_id, = con.execute("""
            INSERT INTO meta_load (snapshot_id, definition_version_id, transform_version, ruleset_version,
                                   resolution_manifest_sha256, parquet_sha256, load_state)
            VALUES (?, ?, ?, ?, ?, ?, 'COMPLETE') RETURNING load_id
        """, [*identity, parquet_hash]).fetchone()
        # Table and column identifiers come only from the fixed DATASETS list.
        con.execute(f"""
            INSERT INTO {fact}
            SELECT ?, p.month_start, d.{dimension}_key, p.unit, p.source_record_number, p.{value}
            FROM read_parquet(?) AS p
            JOIN dim_{dimension} AS d
              ON d.{code} = p.{incoming_code} AND d.definition_version_id = ?
            WHERE p.month_start >= DATE '2014-01-01' AND p.month_start < DATE '2026-01-01'
              AND p.snapshot_sha256 = ?
        """, [load_id, str(parquet), version, expected_hash])
        evidence = {"silver_manifest": manifest, "silver_manifest_path": str(folder / "manifest.json"),
                    "scope": "2014 support plus 2015–2025 reporting",
                    "qualification": "Structural load. Publication gates remain pending."}
        con.execute("INSERT INTO meta_quality_run (load_id, evidence) VALUES (?, ?)",
                    [load_id, json.dumps(evidence)])
    actual, = con.execute(f"SELECT count(*) FROM {fact} WHERE load_id = ?", [load_id]).fetchone()
    if actual != expected_count or digest(parquet) != parquet_hash:
        raise ValueError(f"{name}: expected {expected_count} facts and unchanged Parquet, found {actual}")
    return load_id, actual


def load_warehouse(database, folders):
    database.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(database)) as con:
        con.execute(SCHEMA.read_text(encoding="utf-8"))
        con.execute("BEGIN TRANSACTION")
        try:
            con.execute((ROOT / "sql/create_warehouse.sql").read_text(encoding="utf-8"))
            load_dimensions(con)
            results = [load_fact(con, spec, folder) for spec, folder in zip(DATASETS, folders, strict=True)]
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("supply", "consumption", "import-share"):
        parser.add_argument(f"--{arg}", required=True, type=Path)
    parser.add_argument("--database", type=Path, default=DATABASE)
    args = parser.parse_args()
    results = load_warehouse(args.database, (args.supply, args.consumption, args.import_share))
    for spec, (load_id, rows) in zip(DATASETS, results, strict=True):
        print(f"{spec[3]}: {rows} rows (load {load_id})")


if __name__ == "__main__":
    main()
