# DuckDB warehouse checkpoint

The first warehouse load covers 2014 support history and January 2015 through
December 2025 reporting. The upstream Silver Parquet files preserve the rest of
the source history.

| Table type | Tables | Purpose |
| --- | --- | --- |
| Dimensions | Month, unit, sector, gas source, import category | Describe what each fact measures |
| Facts | Monthly supply, sector consumption, import shares | Store one observation per load, month and category |
| Metadata | Resource, snapshot, definition version, load, quality run | Trace facts to the original CSV and retained validation evidence |

The three facts contain 2,461, 576 and 288 rows respectively, including 2014.
Definition versions remain DRAFT. The load preserves April–June 2021 YETAKUN
as missing and retains the review evidence. Release selection, applicability
decisions, KPI views and dashboard publishing remain separate work.

## How the SQL works

- `CREATE TABLE` defines the columns and constraints. A primary key identifies
  a row. A foreign key requires the referenced dimension or metadata row to exist.
- `generate_series` creates one calendar entry per month, including leap years.
- `INSERT INTO … SELECT` writes facts selected from the Parquet files. The
  `JOIN` resolves the source text code to the warehouse key for the chosen
  definition version. The `WHERE` clause limits the months and snapshot hash.
- The loader checks the inserted counts because an inner join can drop an
  observation when its lookup is missing. `COMMIT` saves all three loads
  together. `ROLLBACK` discards changes from the load transaction if it fails.

This query shows how to read the consumption fact alongside its sector lookup:

```sql
SELECT d.sector_code, f.consumption_rate_mmscfd
FROM fact_gas_consumption_monthly AS f
JOIN dim_sector AS d USING (sector_key)
WHERE f.month_start = DATE '2025-01-01' AND f.load_id = 2
ORDER BY d.sector_code;
```

`SELECT` chooses the columns, `JOIN … USING` pairs the rows on their shared
sector key, and `WHERE` selects one month and one load. `ORDER BY` sorts by
sector code. Load 2 is the consumption load in the verified checkpoint. In
another database use the load ID printed by the loader.

## Rebuild or load the existing warehouse

After generating the three Silver datasets, pass the folders containing their
Parquet files and manifests:

```bash
.venv/bin/python src/gas_pipeline/load_warehouse.py \
  --supply <supply-run-folder> \
  --consumption <consumption-run-folder> \
  --import-share <import-share-run-folder>
```

Replace each placeholder with the actual folder path. The default target is
`data/warehouse/thailand_gas.duckdb`. Close other connections to that file
before loading. An optional `--database` selects another path. Existing matching
manual dimension entries are reused, and conflicting ones cause the load to stop.

The verified local copy is `data/warehouse/checkpoint.duckdb`. The loader ran
twice with identical load IDs and counts. A read-only check confirmed all 144
months, February 2024's 29 days, the category counts, retained quality evidence,
and four January 2025 consumption rows. All 26 existing tests passed.

## First Gold view

`gold.monthly_sector_consumption` exposes the 2015–2025 reporting window for
one explicitly selected consumption load. The view includes the sector code
and display name, exact decimal rate, unit and load ID.

```bash
.venv/bin/python src/gas_pipeline/create_gold_consumption.py \
  --database data/warehouse/checkpoint.duckdb --load-id 2 \
  --silver data/processed/silver/consumption/20261118T154305Z_cd356a0839d7/consumption.parquet
```

Use the consumption load ID and Silver path for your database. The script checks
the Parquet fingerprint and compares all 528 rows before committing the view.

```sql
SELECT sector_name, consumption_rate_mmscfd
FROM gold.monthly_sector_consumption
WHERE month_start = DATE '2025-01-01'
ORDER BY sector_code;
```

`SELECT` chooses the displayed fields, `FROM` reads the saved view, `WHERE`
selects January 2025, and `ORDER BY` sorts by sector code. The view reconciles
the warehouse with Silver. Publication acceptance and KPI calculations remain
separate steps.

### Gold consumption totals and shares

The same Gold creation command also installs
`gold.monthly_consumption_totals` and
`gold.monthly_consumption_sector_shares`. The total groups records by load,
month and unit and sums their reported rates after checking that all four
expected sectors appear exactly once. The share view divides each sector rate
by its monthly total and multiplies by 100. Incomplete months with available
rows return a null total. A zero total returns null shares. Months with no
rows are absent from both views.

Verified 132 monthly totals and 528 shares. The January 2025 total is
4,156 MMSCFD. Sector shares sum to 100% within floating-point precision.
Synthetic checks confirmed incomplete-month and zero-denominator behavior.
GSP includes processing use, so these are reported sector totals.

## Gold supply by source

`gold.monthly_supply_by_source` exposes the 2,277 reported supply rates for
2015–2025 from a single selected load. The dimension join supplies source names,
groups and notes. A left join attaches the import-mix comparison status by month
from the load's stored evidence. National source completeness remains UNRESOLVED.
The view displays existing observations only, so a missing source is never
shown as a measured zero.

```bash
.venv/bin/python src/gas_pipeline/create_gold_supply.py \
  --database data/warehouse/checkpoint.duckdb --load-id 1 \
  --silver data/processed/silver/supply/20261118T154304Z_46083b08eae6/supply.parquet
```

The script checks the selected Silver fingerprint and compares every reporting
row, rate, unit and quality flag before committing the view. April–June 2021
remain REVIEW for import mix.

## Gold published import mix

`gold.monthly_published_import_mix` reads the published EPPO percentages from
one E3 load. It joins the import category dimension for labels and the
denominator description. The denominator is total natural gas imports.
The supply-derived comparison remains available separately as quality evidence.

```bash
.venv/bin/python src/gas_pipeline/create_gold_import_mix.py \
  --database data/warehouse/checkpoint.duckdb --load-id 3 \
  --silver data/processed/silver/import_share/20261118T155029Z_ff96a63f7bcb/import_share.parquet
```

Use the import-share load ID and Silver file for your database. The loader
checks the stored Parquet hash and matches all 264 reporting rows before saving
the view.

## Power BI export checkpoint

Run the following command to export the five Gold views together:

```bash
.venv/bin/python src/gas_pipeline/export_gold.py --database data/warehouse/checkpoint.duckdb
```

The script reads DuckDB in read-only mode and creates a new folder under
`outputs/power_bi/`. Each CSV has headers and a stable sort order. The JSON
manifest records its load ID, row count, and SHA-256. Keep exports outside Git.

For the report, use sector consumption, totals, or sector shares according to
the visual's grain. Use supply by source for reported source rates and retain
its coverage flags. Published import mix is measured on a 0–100 scale. If using
Power BI's percentage format, divide those values and sector shares by 100
first. Use Date for `month_start` and avoid summing rates across months.

## Power BI release check

The current local report is `C:\Users\Admin\GasBI_Checked\Thailand Gas.pbip`.
Keep the short Windows path for Desktop. The imported model reads the five CSVs
from the verified local export run. Refresh on another computer requires pointing
the Power Query sources to that computer's export folder.

Before sharing, open the report in Desktop, refresh all queries, and verify:

- Overview shows 4,304 MMSCFD reported consumption, 1,059 MMSCFD reported LNG,
  and 75.64% LNG share of imports for December 2025.
- The Supply and Import Mix comparison charts respond to month and category
  slicers. Two selected months appear separately. The fixed-period cards keep
  their stated reporting months.
- The Supply and Overview coverage notes remain visible. Label the supply
  group figures as sums of available records and the import percentages as
  shares of total imports.

The five CSV hashes and row counts were rechecked against the export manifest,
and the expected December figures were checked against the CSVs. The report
is limited to reported source supply, sector consumption, and published import
mix. National supply completeness and import dependence are pending. Live
Desktop refresh and the publishing decision remain open.
