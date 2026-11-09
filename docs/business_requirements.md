# Thailand Natural Gas Supply & Demand: A Data Warehouse and BI Dashboard

Status: proposed requirements, assessed 10 November 2026 (Asia/Bangkok). This is an independent internship portfolio project, not an official PTT publication. The repository is named Thailand-Natural-Gas-Supply-Demand-A-Data-Warehouse-and-BI-Dashboard; the existing Python setup is retained.

## Purpose and users

Help an analyst explain how Thailand's reported gas supply mix and sector consumption change over time. The intended reader is a business reviewer who needs understandable monthly trends and traceable numbers, rather than operational dispatch or procurement advice. The evidence and access limitations are in [source assessment](source_assessment.md).

## Business questions

| Question | Proposed view or measure | Important qualification |
| --- | --- | --- |
| How has reported supply changed month to month and year to year? | Total EPPO supply trend; MoM and YoY changes | Compare the same source boundary and unit. |
| Which sources explain supply changes? | Source-level contribution to YoY change; separate LNG, pipeline imports, JDA, and other sources | Preserve original source names and avoid overlapping categories. |
| How much of reported supply comes from imports? | Import dependence; pipeline and LNG shares of total supply | This differs from the mix within imports. |
| Is the mix of imported gas changing? | LNG versus Myanmar share of imports | Validate against EPPO's separate import-share dataset. |
| Which sectors use the gas, and which drive changes? | Consumption and shares for electricity, gas separation plants, industry, and NGV | GSP is a processing category, not necessarily final end-use demand. |
| Do supply and consumption move together? | Side-by-side monthly trends | Do not describe their difference as a physical gas balance or unmet demand. |
| How reliable and current are the numbers? | Source, latest observation month, missing periods, and validation flags | A catalogue update date is not a data observation date. |

## Feasible first release

Use EPPO supply and sector-consumption CSVs as the core; use EPPO import shares as a validation reference. Start with January 2015–December 2025: all 132 months occur in both core downloads and each month has all four sectors. January–July 2026 is an optional, separately labelled partial year, not a full-year comparison. These are observed file limits as of the assessment, not a promise of future publication.

Use DMF domestic supply only as a separate comparison series after reviewing definitions. Defer DMF field/block production integration: its units, naming changes, and duplicate candidate keys require investigation. Do not add DMF supply to EPPO supply: these describe overlapping activity.

Deferred: forecasting, prices and costs, carbon estimates, terminal utilisation, cargo-level LNG analysis, province-level demand, confidential PTT information, full ETL, warehouse implementation, and dashboard construction. The work now is documentation and feasibility only.

## Monthly reporting grain

“Grain” means what one row represents. Use Gregorian calendar months, represented by their first day, not fiscal years. Preserve the source year and calendar alongside the converted year. DMF production uses Buddhist Era years (subtract 543); the inspected EPPO and DMF domestic-supply files already use Gregorian years.

| Proposed fact | One row represents | Key and measure |
| --- | --- | --- |
| Supply | One month × EPPO source × unit, for Thailand's reported supply system | Month, source, unit; reported average daily rate |
| Consumption | One month × EPPO sector × unit | Month, sector, unit; reported average daily rate |
| Import-share reference | One month × import category | Month, category; publisher's percentage |
| DMF comparison, optional | One month × reported area type × unit | Month, area, unit; a separate reported rate |

Preserve source URL, resource ID, retrieval timestamp, file SHA-256, original unit, and any revision label with each source snapshot. Proposed lookup dimensions are month, source, sector, and provenance. These are design notes, not an implemented schema. Aggregate each fact to month before comparing facts: joining raw supply rows to raw sector rows would multiply values.

## Classification and units

- MMSCFD means million standard cubic feet per day: a **rate**, not a month's total volume. The EPPO CSVs explicitly label every inspected row `MMSCFD`.
- EPPO's `LNG` row already uses gas volume. Retain it as “LNG, as reported by EPPO (MMSCFD)”; do not claim to have measured LNG cargo mass or performed a conversion.
- Proposed pipeline-import mapping: `YADANA`, `YETAKUN`, `ZAWTIKA`; LNG-import mapping: `LNG`. This mapping reproduces the separate published LNG import-mix percentages within 0.1 percentage point over the selected period. Record it as a project mapping, not a supplied classification column.
- Retain `JDA` as its own joint-development source category. Include it once in total reported supply. Do not silently label it a sovereign domestic field or an import. Keep `OTHERS` visible as an aggregated source; seek EPPO's category notes before publishing a definitive domestic-only measure. Unknown new source names must trigger review.
- Electricity = `ELECTRICITY`; gas separation plants = `GSP`; industry = `INDUSTRY`; natural gas for vehicles = `NGV`. Call their sum “reported sector consumption”, a demand proxy rather than all possible final demand.
- Do not combine LNG tonnes, NGL, LPG, condensate barrels, oil-equivalent production, and natural-gas volume. DMF's Thai liquid-product labels must not be assumed to mean LNG.
- Any later mass-to-volume conversion needs an authoritative factor, composition/density or heating-value assumptions, standard pressure/temperature basis, formula, units, applicable dates, citation, and a stored conversion version. Otherwise, display incompatible units separately. No mass conversion is authorised or required for this scope.

## KPI definitions

For a complete month `m`, define `S_m` as the sum of EPPO source rates, `P_m` as mapped pipeline imports, `L_m` as the EPPO LNG rate, `I_m = P_m + L_m`, and `C_m` as the sum of the four consumption sectors. All rates below are MMSCFD. Supply mappings and source completeness must be approved before publishing import dependence.

| KPI | Definition | Display / interpretation |
| --- | --- | --- |
| Total reported supply | `S_m` | MMSCFD; includes JDA and OTHERS once |
| Imported supply | `I_m` | MMSCFD; not an extra row added to source totals |
| Import dependence | `100 × I_m / S_m` | % of total reported supply |
| LNG / pipeline share of total supply | `100 × L_m / S_m`; `100 × P_m / S_m` | %; these sum to import dependence, not 100% |
| LNG share of imports | `100 × L_m / I_m` | %; compare with EPPO import-share reference |
| Reported sector consumption | `C_m` | MMSCFD; explain inclusion of GSP |
| Sector share | `100 × sector_rate_m / C_m` | %; four sectors sum to approximately 100% |
| MoM / YoY rate change | `100 × (X_m / X_previous − 1)`; previous = prior month / same month last year | %; valid for total or component rates |
| Source / sector contribution to YoY change | `X_component,m − X_component,m−12` | MMSCFD; signed contributions sum to total change if categories align |
| Change in a share | `share_m − share_m−12` | Percentage points, not percent growth |
| Data freshness | Latest observed month and retrieval time | Show both; do not infer freshness from metadata alone |

Missing, unknown, or zero denominators produce “not available”, never zero or infinity. Compare only aligned months with complete required components. Do not fill a missing source record with zero unless source documentation explicitly supports that interpretation; source lists change over time.

For annual or YTD rates use day weights: `sum(rate_m × calendar_days_m) / sum(calendar_days_m)`, over complete included months. A derived monthly volume is `rate_m × calendar_days_m`, in **million standard cubic feet**, only after confirming that the published rate is averaged across all calendar days. Never sum daily rates across months and label the result a volume. Do not substitute DMF's `DAYSOFPRODUCE` for calendar days without confirming its meaning. Compare YTD only with the same months of the previous year. Recompute multi-month shares from weighted component rates or compatible volumes, not an unweighted average of monthly percentages.

Supply and consumption may differ because of statistical boundaries, processing, own use, losses, and timing; these are possible explanations requiring evidence, not measured adjustment series here. No “shortage”, “surplus”, or inventory KPI is approved.

## Acceptance criteria for a later implementation

| ID | Pass condition |
| --- | --- |
| AC1 — Traceability | Every included series links to a verified official resource and a dated, hashed raw snapshot. Raw files remain under ignored `data/raw/`; no raw source rows, secrets, or environments are staged. |
| AC2 — Coverage | The baseline contains 132 unique months from 2015-01 to 2025-12 in both core facts, four sectors per month (528 sector rows), and no duplicate month/category/unit keys. Any later change to coverage is explicit. |
| AC3 — Classification | Every supply name has a reviewed mapping or an explicit unresolved label; JDA and OTHERS have documented treatment. Validate aggregate boundaries against an official reference before publishing domestic-only supply or import dependence. No unresolved material source is silently defaulted to domestic. |
| AC4 — Units | Only compatible source rates enter totals. Original `UNIT` is retained and checked. No mass/volume addition or undocumented LNG conversion occurs. DMF production's unit ambiguity blocks its integration. |
| AC5 — Reconciliation | For January, June, and December 2025, manually check every displayed source and sector value against the downloaded CSV at published precision. Component sums and KPI formulas recompute correctly; displayed sector shares sum to 100% within 0.1 percentage point after rounding. |
| AC6 — Import reference | For all 132 baseline months, calculated LNG share of imports differs from EPPO's reference by at most 0.1 percentage point; flag larger differences rather than overwrite values. This checks import mix, not the total-supply denominator. |
| AC7 — Quality | Nulls, duplicate keys, unexpected categories, negative rates, missing months, source revisions, and data beyond the stated reporting cutoff generate a review record. Zero is retained when actually reported; missing is not coerced to zero. Exact DMF duplicates require a logged policy, not silent deduplication. |
| AC8 — Time calculations | MoM and YoY use calendar offsets, not previous available row. Missing comparison months and zero denominators return unavailable. Partial-year labels, day weighting, and like-for-like YTD rules are demonstrated. |
| AC9 — Communication | A reviewer can identify each chart's unit, time window, source, and last observation. GSP, JDA, import dependence versus import mix, and incomplete years have plain-language explanations. No causal or physical-balance claim exceeds the data. |
| AC10 — Scope | Existing environment remains usable; only approved public sources are used. Pipeline and BI work starts in a later task after source definitions and these requirements are reviewed. |

## Current environment check

On 10 November 2026, the existing isolated `.venv` runs Python 3.14.4 and JupyterLab 4.6.6. `pip check` passed. During the initial assessment, the legacy retail smoke test passed dataframe SQL, SQLite, Excel/Parquet round trips, plotting, and executed notebook checks. That retail-specific script and the incomplete secondary environment were subsequently removed during project cleanup. The working `.venv` and dependencies were retained. No package changes were needed for this assessment.
