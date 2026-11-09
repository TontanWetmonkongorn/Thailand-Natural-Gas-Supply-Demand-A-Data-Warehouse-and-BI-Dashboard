# Official source assessment and feasible scope

Assessment date: 10 November 2026 (Asia/Bangkok). EPPO = Energy Policy and Planning Office; DMF = Department of Mineral Fuels. Findings below distinguish file contents from catalogue claims. Public availability does not mean this project is endorsed by either agency or PTT.

## Verification method

Inspected official catalogue metadata and downloaded five linked resources with HTTP GET. All five returned HTTP 200 and parsed as CSV. Download links were obtained from agency CKAN metadata or the official government catalogue, not constructed from guessed filenames. Initial EPPO CSV attempts returned HTTP 403; retrying with a browser-style `User-Agent: Mozilla/5.0` and `Referer: https://catalog.eppo.go.th/` succeeded. Access can change; do not assume an API is required or guaranteed.

The local assessment snapshots and metadata are under ignored `data/raw/source_assessment/`. They are investigation evidence, not a pipeline. No source rows or downloads are committed. CSV inspection checked columns, units, minimum/maximum month, missing months, nulls, and candidate duplicate keys. A month occurring in a file does not by itself prove every possible production source was reported.

## Downloaded resource inventory

All coverage below is **observed in the downloaded file**, unless explicitly described as metadata. Row counts exclude headers.

| ID | Publisher / dataset | Observed coverage and grain | Format, encoding, unit | Role |
| --- | --- | --- | --- | --- |
| E1 | EPPO production and imports | 1986-01–2026-07; 487 distinct months; 4,925 month/source rows | UTF-8 BOM CSV; `Quantity`, `UNIT=MMSCFD` | Core supply |
| E2 | EPPO sector consumption | 1986-01–2026-07; 487 distinct months; 1,728 month/sector rows | UTF-8 BOM CSV; `Quantity`, `UNIT=MMSCFD` | Core consumption |
| E3 | EPPO import mix | 2000-01–2026-07; 638 month/category rows | UTF-8 BOM CSV; `Share`, `UNIT=%` | Validate LNG/Myanmar import composition |
| D1 | DMF domestic supply | 2010-01–2026-01; 191 rows, 189 distinct months | CSV decoded as Windows-874 (`cp874`); `GASPROD_UNIT=MMSCFD` | Optional comparison |
| D2 | DMF gas production | 2003-01–2026-03; 279 distinct months; 11,635 rows by field/group and block context | CSV decoded as `cp874`; numeric `GAS`; unit/basis requires reconciliation | Defer integration |

### E1 — EPPO production and import of natural gas

- [Official dataset](https://catalog.eppo.go.th/dataset/dataset_11_20)
- [Verified metadata JSON](https://catalog.eppo.go.th/api/3/action/package_show?id=dataset_11_20)
- [Direct CSV](https://catalog.eppo.go.th/dataset/799ad6f1-db30-4910-8d21-7ec670a7ba89/resource/7a74d96f-d988-4588-b1d1-8e7824c0d08c/download/dataset_11_20.csv)
- Resource ID: `7a74d96f-d988-4588-b1d1-8e7824c0d08c`.

Columns: `Year, Month, Source, Quantity, UNIT`. GET the CSV; no login was needed in the successful check. Metadata describes monthly updates and processing of DMF production/import reports. Its last-data-year field says BE 2567 (2024), while the CSV reaches July 2026. Use file dates, not that stale metadata field.

No nulls or duplicate `(Year, Month, Source)` keys were observed; all 487 months occur. The 2015–2025 subset has 2,277 rows across 132 months. Source membership changes; there is no explicit domestic/import classification column. `LNG` is already MMSCFD, not tonnes. Preserve `JDA` and `OTHERS` separately; do not assume absent source records mean zero. The integers imply published rounding.

### E2 — EPPO consumption of natural gas by sector

- [Official dataset](https://catalog.eppo.go.th/dataset/dataset_11_22)
- [Verified metadata JSON](https://catalog.eppo.go.th/api/3/action/package_show?id=dataset_11_22)
- [Direct CSV](https://catalog.eppo.go.th/dataset/26f29bb9-fc1e-4a62-a39d-817188a74810/resource/f69c137e-168c-473c-beb0-2f49a3dc076f/download/dataset_11_22.csv)
- Resource ID: `f69c137e-168c-473c-beb0-2f49a3dc076f`.

Columns: `Year, Month, Sector, Quantity, UNIT`. GET the CSV with the EPPO headers described above. Metadata describes monthly updates and compilation from sources including PTT and EGAT. The metadata's 2024 endpoint is stale relative to the file.

Observed labels are `ELECTRICITY`, `GSP`, `INDUSTRY`, and `NGV`. There are no nulls or duplicate month/sector keys. The 2015–2025 subset has exactly 528 rows, four per month. Earlier history does not have four sectors in every month. GSP includes processing use: label the sum reported sector consumption rather than final consumer demand. These are national sector statistics, not company customers or provincial demand.

### E3 — EPPO natural gas and LNG import shares

- [Official dataset](https://catalog.eppo.go.th/dataset/dataset_11_82)
- [Direct CSV](https://catalog.eppo.go.th/dataset/b3a14e20-8240-4b3e-9021-f0c88b5225be/resource/293c5cb3-d384-4242-a036-5552567ae482/download/dataset_11_82.csv)
- Discovery: [official natural-gas dataset group](https://catalog.eppo.go.th/dataset/?_tags_limit=0&groups=nature-gas), also inspected through its CKAN catalogue search.
- Resource ID: `293c5cb3-d384-4242-a036-5552567ae482`.

Columns: `Year, Month, Source, Share, UNIT`; source labels `LNG` and `MYANMAR`. GET returns CSV without authentication using the EPPO headers. Metadata describes monthly percentage reporting, with a stale 2024 endpoint. Baseline 2015–2025 has 264 rows, two per month, and no duplicate keys.

These percentages describe the **mix within imports**, not imports as a percentage of all supply. As a consistency check, `100 × LNG / (LNG + YADANA + YETAKUN + ZAWTIKA)` from E1 agreed with E3 within 0.048 percentage point across 180 overlapping months with computable values, including the baseline. This supports the proposed import mapping but does not settle JDA, other-source boundaries, or domestic-only definitions.

### D1 — DMF domestic natural gas supply

- [Official agency dataset](https://catalog.dmf.go.th/dataset/supply-natrarl-gas)
- [Verified metadata JSON](https://catalog.dmf.go.th/api/3/action/package_show?id=supply-natrarl-gas)
- [Government catalogue record](https://data.go.th/dataset/supply-natrarl-gas)
- [Direct CSV](https://catalog.dmf.go.th/dataset/41a5ca9e-b199-4c02-9cc0-e4ba65e3ef25/resource/0ecb6230-f211-4fc2-9363-a10020ede766/download/supply_th_gas.csv)
- Resource ID: `0ecb6230-f211-4fc2-9363-a10020ede766`.

GET downloads a CSV despite the XLSX MIME type. Columns: `MONTH, YEAR, AREATYPE, GASPROD_UNIT, GASPROD`. The inspected year is Gregorian; area is `ในประเทศ` (domestic). The file has monthly observations, but metadata says **annual updates** and claims 2010–2025; actual observations extend to January 2026.

September–December 2010 are absent. March and September 2012 each appear twice with identical values. The 2015–2025 window has twelve observations per year. Rows are unsorted. Domestic supply is not automatically the same boundary as gross production or EPPO non-import supply, particularly around JDA and processing. Use as a separately labelled reference until definitions are reconciled, never as additional supply.

### D2 — DMF production by field/group

- [Official agency dataset](https://catalog.dmf.go.th/dataset/production-natural-gas)
- [Verified metadata JSON](https://catalog.dmf.go.th/api/3/action/package_show?id=production-natural-gas)
- [Government catalogue record](https://data.go.th/th/dataset/production-natural-gas)
- [Direct CSV](https://catalog.dmf.go.th/dataset/ad91d31d-7e3b-48a3-b454-53c174156705/resource/f86d5605-e407-461f-83d8-47f9b4bd0803/download/production_gas.csv)
- [Official January 2026 report](https://dmf.go.th/public/createpetroleum/data/report/menu/1114/year/2569/month/1)
- Resource ID: `f86d5605-e407-461f-83d8-47f9b4bd0803`.

GET downloads CSV despite an Excel MIME type. Columns include `YEAR, MONTH, BLOCK_TYPE, BLOCK, SOURCE_GROUP, GAS, GAS_EQUI_OIL, DAYSOFPRODUCE`. Metadata says monthly updates and million cubic feet, whereas the report labels gas million cubic feet/day. The CSV has no unit column; confirm its exact rate basis before calculations. Years are Buddhist Era, not Gregorian.

There are 7,799 missing block values, two blank-measure records, and 46 duplicate candidate keys `(YEAR, MONTH, BLOCK_TYPE, BLOCK, SOURCE_GROUP)`; this does not establish that all 46 are erroneous duplicates. Names and grouping change; one label explicitly mentions LPG and kilograms. Metadata's 2024 endpoint is stale. The report offers PDF/Excel controls, but those export routes were not verified. Defer this resource from core totals.

## Access, licensing, and reproducibility notes

The inspected agency catalogue metadata labels these resources `Open Data Common` and public/no restricted access where specified. Preserve attribution and verify the precise redistribution terms before republishing datasets; this project currently commits documentation only.

Use the resource Download link for manual retrieval. For repeatable retrieval later, GET the exact CSV URL above, save bytes under `data/raw/`, record the retrieval timestamp and SHA-256, then parse according to the file contents rather than HTTP MIME type. For example, after creating the ignored destination directory:

```bash
mkdir -p data/raw/source_assessment
curl --fail --location --max-time 60 \
  --user-agent 'Mozilla/5.0' \
  --referer 'https://catalog.eppo.go.th/' \
  'https://catalog.eppo.go.th/dataset/799ad6f1-db30-4910-8d21-7ec670a7ba89/resource/7a74d96f-d988-4588-b1d1-8e7824c0d08c/download/dataset_11_20.csv' \
  --output data/raw/source_assessment/eppo_supply.csv
```

EPPO's [separate statistics API documentation](https://apidoc.eppo.go.th/) was discoverable in search but live access failed (HTTP 522 in the direct check). CKAN DataStore attempts returned 403. Neither is needed for the verified CSV approach; do not claim either has been tested successfully. Some government-catalogue previews expose unrendered placeholders, so a preview failure does not prove the linked file is unavailable.

These snapshots can be revised in place. Min/max dates do not guarantee completeness for every category. Do not substitute publication years for observation years, infer cause from trend lines, or assume supply and consumption use identical measurement boundaries.

### Download fingerprints

SHA-256 of the exact downloaded bytes on the assessment date; useful for detecting later revisions, not a substitute for retaining the local raw snapshot.

| ID | Local filename | SHA-256 |
| --- | --- | --- |
| E1 | `eppo_supply.csv` | `cf57ec62948aedc61546b26c76d29d823b1b5e10a829c2269f1dd8d2000ab4e4` |
| E2 | `eppo_consumption.csv` | `7fddd2cb1f91916182bd4f45c869a64b62b8a4ff1bd047d67b58f573f8ea91e9` |
| E3 | `eppo_import_share.csv` | `dc6bf80391bd742ddeaeb02658f3eb7768aaba00da2db99f7d351be6d815a050` |
| D1 | `dmf_supply.csv` | `f802353d9d76f38a71047b87858fb843c08299ada6c6fc848bbf35b717ad5a20` |
| D2 | `dmf_production.csv` | `73a7de7ac26f192c0919d5a136d1ec945c22767e3fc661625b76f94533752378` |

## Recommended scope and decision gates

**Proceed with an EPPO-led monthly portfolio study for 2015–2025.** Both core files contain all 132 months; consumption has all four sectors. The third EPPO file supplies an independent published import-mix check. Add January–July 2026 only as a partial-year extension, compared with the same months of 2025.

The eventual BI story can have three pages: supply/source trends, imports and import dependence, and consumption by sector. This describes a feasible future deliverable, not work implemented now. The existing pandas, DuckDB, SQLAlchemy, and Jupyter environment is sufficient for the next stage; no dependency installation was necessary.

Before implementation, review the source mapping and the handling of JDA/OTHERS against EPPO's statistical definitions. Withhold definitive domestic-only labels and final import-dependence claims until those boundaries are documented. Use the [business requirements](business_requirements.md) for formulas and acceptance criteria. Treat D1 as an optional comparison, and defer D2 field-level integration until the unit basis and candidate-key anomalies are resolved.

If download access later fails, use a previously retained, dated snapshot and clearly label its cutoff; never fabricate missing observations or present 2026 as complete. No full pipeline, database, forecast, or dashboard has been built in this assessment.
