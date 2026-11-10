# Warehouse design, explained in small steps

Status: design in progress, started 11 November 2026 (Asia/Bangkok). This document grows one sub-step at a time. No database, SQL schema, or pipeline has been created.

Follow the [business requirements](business_requirements.md), [source assessment](source_assessment.md), and [quality rules](data_quality_rules.md). Table names below are design proposals, not existing database objects.

## Learning sequence

| Sub-step | Design question | Status |
| --- | --- | --- |
| 5.1 | What does one measurement row represent? | Documented below |
| 5.2 | Which descriptive lookup tables (dimensions) do we need? | Documented below |
| 5.3 | Which columns, data types, and keys should the tables have? | Pending |
| 5.4 | How will source snapshots, revisions, and quality decisions be tracked? | Pending |
| 5.5 | How do the tables relate, and how can queries avoid double-counting? | Pending |
| 5.6 | Does the complete design support the scope, KPIs, and quality rules? | Pending |

## 5.1 — Decide what one row represents

### Start with the observation, not SQL

Before creating tables, finish this sentence: **“One row represents…”** Database designers call this the table's **grain**. It tells us how much detail each record contains and what must distinguish one record from another.

The existing EPPO files already describe three different kinds of observations:

| Proposed measurement table | One row represents | Measured value | Original columns that explain it |
| --- | --- | --- | --- |
| `fact_gas_supply_monthly` | One month's reported gas-supply rate for one EPPO source, in its stated unit, within a selected source snapshot | Supply rate, MMSCFD | `Year`, `Month`, `Source`, `Quantity`, `UNIT` |
| `fact_gas_consumption_monthly` | One month's reported gas-consumption rate for one EPPO sector, in its stated unit, within a selected source snapshot | Consumption rate, MMSCFD | `Year`, `Month`, `Sector`, `Quantity`, `UNIT` |
| `fact_import_share_monthly` | One month's published share of imports for one EPPO import category, within a selected source snapshot | Share, % | `Year`, `Month`, `Source`, `Share`, `UNIT` |

Here, **fact** means a recorded numerical observation. “Monthly” means the rate is reported for a month; it does not turn MMSCFD into a monthly volume. Snapshot means the particular version of the publisher's file. Version-selection and physical keys will be designed in later sub-steps.

### Why three measurement tables?

Supply answers **where gas comes from**. Consumption answers **which sector uses it**. Import share answers **what fraction of imports belongs to a category**. These have different categories and, for shares, different units and aggregation rules.

The `Source` column in the import-share file is not the same category set as `Source` in the supply file: MYANMAR is a published import-share category, while supply reports the three Myanmar sources individually. A common column name does not prove that two records have the same meaning.

Do not create a table whose rows imply “this source supplied this sector”. These national files do not tell us which producing source delivered gas to which consuming sector. Such an allocation would be invented.

### What the grain prevents

- A month alone cannot identify a supply record: several sources occur in the same month. A supply source alone also cannot identify it: that source occurs across many months.
- Repeated observations for the same month/category/unit within a snapshot require review. A numeric value must not be included in the identity merely to make conflicting observations appear unique.
- Directly joining source rows to sector rows on month repeats each source across sectors. Do not sum the resulting repeated values. Later comparison queries must aggregate each measurement table to a compatible grain before joining.
- A source can disappear from the file without that absence proving zero. Do not manufacture a complete source-by-month grid of zero measurements.
- The same month/category can legitimately have different reported values in different file revisions. A reporting release must select its snapshot rather than sum revisions together.

### Scope at this grain

The first reporting window remains January 2015–December 2025, with 2014 available only for comparison history. DMF numerical integration and 2026 reporting are deferred. Raw source files remain unchanged and outside Git.

This sub-step defines the measurement grain only. It does not choose primary keys, create dimensions, implement duplicate handling, or prove data quality. Those are separate decisions.

The next section adds the descriptive tables that accompany these measurements.

## 5.2 — Choose descriptive lookup tables

### Facts measure; dimensions describe

A **dimension** is a lookup table of descriptions. A fact records a measurement and refers to the relevant descriptions. For example, a supply measurement refers to a month, a gas source, and a unit. The source's display name and reviewed domestic/import classification belong with its description, not inside the measured quantity.

Dimensions give charts consistent labels and filters. They do not establish that an observation is complete, fix missing values, or prove that similarly named sources are the same thing.

### Five proposed dimensions

These are conceptual descriptions, not a final list of SQL columns or populated tables.

| Proposed dimension | One descriptive row represents | Descriptive information | Used by |
| --- | --- | --- | --- |
| `dim_month` | One Gregorian calendar month | Month start, year, month number/name, and calendar-day count | All three facts |
| `dim_gas_source` | One reviewed EPPO gas-source concept | Original source code, readable label, domestic/Myanmar-import/LNG-import group, and classification qualification | Supply fact |
| `dim_sector` | One reported consumption sector | Original sector code, readable name, and explanatory note | Consumption fact |
| `dim_import_category` | One category in the published import-share reference | Original category code and description of its percentage denominator | Import-share fact |
| `dim_unit` | One measurement unit used in this release | Unit code, readable meaning, and whether it is a rate or percentage | All three facts |

**Month:** Create a shared calendar description so January is the same month in all three facts. The selected design needs January 2014–December 2025, 144 calendar months: 12 supporting months and 132 reporting months. A calendar row may exist even when an observation is missing; its existence must not generate a zero-valued fact. Which months are displayed belongs to the release/report filter, not a claim that 2014 is outside the calendar. Storing a day count does not itself authorise rate-to-volume conversion.

**Gas source:** ERAWAN can have a readable label and EPPO-defined domestic classification. JDA remains explicitly joint-development within EPPO's domestic grouping; OTHERS remains an aggregate. “One source” therefore does not always mean one physical gas field. Preserve raw source text in load lineage separately. Changes to grouping require versioned evidence; this design must not overwrite historical meanings with today's description. The mechanism will be addressed with keys and provenance in later sub-steps.

**Sector:** ELECTRICITY means electricity generation, GSP means gas separation plants, INDUSTRY means industry, and NGV means gas for vehicles. A description can explain that GSP is processing use rather than final consumer demand. The expected four sectors do not prove each month's four measurements are present; that is a separate validation check.

**Import category:** Keep LNG and MYANMAR as reference categories with the denominator “total imports”. Do not reuse the gas-source lookup for MYANMAR: supply instead has YADANA, YETAKUN, and ZAWTIKA as separate sources. LNG also occurs in both datasets, but an import-share percentage and a supply rate remain separate facts. Their common wording does not authorise adding or directly joining their measurements.

**Unit:** MMSCFD describes a daily gas-volume rate; % describes a share. Retain the Myanmar heat-value qualification with the series/source evidence, not as an assumption applying to every MMSCFD observation. A unit lookup supplies meaning, not a conversion factor. Yearly rates and percentages still need the aggregation rules in the requirements.

### How a fact uses these descriptions

Conceptually, a supply record says: “For this month and this gas source, the reported rate in this unit is the recorded value.” It references the corresponding dimension rows. Changing a chart's source display label should not require changing its numerical measurements. Physical reference columns and constraints will be chosen in 5.3.

Multiple facts can refer to one month description. This supports a common time filter; it does **not** make it safe to join raw supply and consumption facts together on month and sum the repeated rows.

### What we are deliberately not adding yet

- No source-to-sector allocation dimension: the public files do not supply that relationship.
- No field/block, customer, province, or LNG-cargo dimensions: those are outside the selected release.
- No country lookup for now: the reporting system is national, and JDA must not be reduced to an unsupported exclusive-country claim.
- File snapshots, publisher identity, retrieval details, mapping versions, and quality decisions remain necessary metadata; their table design belongs to 5.4. “Gas source” and “source file/publisher” are different concepts.

Sub-step 5.2 selects the descriptive concepts only. No dimension rows, database, keys, or pipeline have been created.

**Next sub-step: 5.3 — choose columns, data types, and keys.**
