# Cleaning and validation rules

Version 1, documented 11 November 2026 (Asia/Bangkok). These are **project rules for later implementation**, not claims that a pipeline exists or that data has passed acceptance. No raw records are changed by this document.

Use the [selected scope and KPI definitions](business_requirements.md) and [source evidence](source_assessment.md) alongside these rules. “Cleaning” means creating a traceable, standardised analytical representation; it does not mean repairing the publisher's original file in place.

## 1. Inputs and provenance

- First-release inputs are the retained EPPO supply (E1), consumption (E2), and import-share (E3) CSV snapshots. Report January 2015–December 2025; retain 2014 only for comparison history. Preserve other years and all DMF records in raw storage, outside first-release reporting.
- Use the documented SHA-256 fingerprints to identify snapshots. A URL can return different bytes later: a different hash means a new revision, not a replacement authorised by the existing assessment.
- In a later load, record resource ID, official URL, file hash, filename, original row number, encoding, retrieval time when known, inspection time, and the transformation/rule version. Keep workbook sheet/cell references when used as evidence.
- For legacy downloads, record unknown retrieval timestamps as unknown and retain the known assessment/verification dates. Do not manufacture precise download times from file modification times. Disclose incomplete provenance before release; obtain a newly dated snapshot separately if reproducibility requires it.
- Store raw downloads under ignored `data/raw/`. Never overwrite an earlier snapshot, edit its values, or commit raw files. The workbooks support classification and reconciliation; they must not silently replace CSV values.

## 2. Parsing and allowed values

| Input | Required columns | Original encoding and checks |
| --- | --- | --- |
| E1 supply | `Year, Month, Source, Quantity, UNIT` | UTF-8 with optional BOM; `UNIT` must be MMSCFD |
| E2 consumption | `Year, Month, Sector, Quantity, UNIT` | UTF-8 with optional BOM; `UNIT` must be MMSCFD |
| E3 import shares | `Year, Month, Source, Share, UNIT` | UTF-8 with optional BOM; `UNIT` must be % |

Reject unreadable files, duplicate column headers, malformed records, and missing required columns from analytical loading. Unexpected columns require schema review; do not silently discard them. Do not assume the HTTP MIME type is correct: some assessed DMF CSV downloads advertise Excel MIME types.

Preserve original text alongside parsed values. Remove a BOM from a header and trim outer whitespace in a separate standardised field, logging changes. Do not remove meaningful punctuation or internal spaces, guess a different encoding after replacement characters appear, or silently coerce malformed numbers to zero.

Parse numeric values as finite numbers, not text. Reject NaN, infinity, unsupported numeric notation, and negative gas rates. Shares must be between 0 and 100 inclusive. A failed parse remains an issue tied to its original record, not a dropped row. Do not round values before calculations; use display rounding only at the end. Integer-valued source data does not by itself prove a particular rounding method.

## 3. Dates and reporting window

- EPPO years are Gregorian in the assessed files. Parse `Year` as an integer and full English `Month` names using an explicit January–December lookup. Invalid, missing, or ambiguous dates require review; never infer a month from row order or use the computer's current year.
- The analytical month is its first calendar day; preserve original year/month fields. Require one of the 132 expected reporting months for reporting records. Valid 2014 dates are support history; other valid dates are outside the selected scope, not bad records to delete.
- The retained CSVs end at July 2026. A later observation or changed file is a revision/scope review trigger, not permission to extend the report automatically. Impossible future dates also require review.
- Use calendar offsets for MoM/YoY, not the preceding available row. An unavailable comparison period produces an unavailable result. January 2015 MoM can use December 2014; 2015 YoY can use the matching 2014 month only if the required series and boundaries are comparable.
- DMF production uses Buddhist Era years; a future implementation would explicitly subtract 543 after confirming the dataset calendar. DMF domestic supply already uses Gregorian years. Do not apply calendar conversion to every Thai-source file merely because it is Thai.

## 4. Labels and classification

Retain the raw label and map it explicitly to a reviewed analytical label. The [workbook evidence](source_assessment.md#step-1-follow-up-source-definitions-11-november-2026) supports the following grouping:

| Group | Exact EPPO CSV labels |
| --- | --- |
| Domestic, EPPO classification | `ERAWAN`, `BONGKOT`, `BONGKOT TAI`, `PAILIN`, `ARTHIT`, `TANTAWAN`, `PHU HORM`, `SIRIKIT`, `LANTA`, `NAM PHONG`, `JASMINE`, `YOONG THONG`, `JDA`, `OTHERS` |
| Myanmar imports | `YADANA`, `YETAKUN`, `ZAWTIKA` |
| LNG imports | `LNG` |
| Consumption sectors | `ELECTRICITY`, `GSP`, `INDUSTRY`, `NGV` |
| Import-share reference categories | `LNG`, `MYANMAR` |

Use “Domestic supply—EPPO classification, including JDA”. Keep JDA visible; do not adjust its reported quantity for ownership. Keep OTHERS as an aggregate with unknown individual-field composition. E3 MYANMAR is a reference percentage category, not an extra E1 volume source.

New names, spelling variants, and many-to-one mappings require evidence and a versioned mapping decision. Do not use fuzzy matching to merge producing fields. Workbook variants such as Jasmin versus CSV JASMINE may be mapped as documented; they do not authorise merging similarly named DMF fields or applying today's grouping to all historical records. If two raw labels map to the same analytical key, flag the collision before aggregation.

## 5. Missing, zero, and changing source membership

**Zero is an observed number; missing means the value is unknown.** Keep them distinct.

| Situation | Required treatment |
| --- | --- |
| A source explicitly reports `0` | Retain zero as reported; do not treat it as missing. |
| Blank value, missing row, or unrecognised missing-value marker | Preserve its original representation, flag it, and withhold dependent calculations. Do not forward-fill, interpolate, or substitute zero. |
| A required reporting month is absent | Flag the gap; dependent monthly KPIs and full-year summaries are unavailable. |
| E2 has fewer/more than the four expected sectors in a month | Block that month's consumption total and sector shares pending review. |
| E3 lacks either LNG or MYANMAR | Mark import-reference validation unavailable for that month; block a claim that all baseline validation passed. |
| A supply source appears/disappears or changes group | Record a membership change and review the affected months. Do not force a fixed 18-source panel. |

The baseline E1 file has 15–18 source rows per month. For the later implementation, maintain a reviewed month/source applicability register: **expected**, **documented not applicable**, or **unresolved**. Establish applicability from publisher notes and retained table evidence; first/last occurrence in the CSV alone is insufficient. A workbook blank alone is also insufficient to establish zero.

An expected source requires a valid observation. A documented-not-applicable source may be excluded from that month's required set with its evidence recorded, without creating a zero-valued source record. Any unresolved applicability or missing expected value makes completeness unresolved. A partial sum may be inspected as “sum of available records”, but must not be published as complete national supply or used for import dependence. If the expected set cannot be established, retain that limitation rather than claiming completion.

The four mapped import sources require the same applicability review; do not let a summation silently ignore an absent import row. Source-level growth and contribution comparisons require compatible categories in both periods; any regrouping must be reviewed before claiming that contributions explain total change.

## 6. Duplicate records and revisions

- Check keys **within one selected snapshot**: E1 = month/source/unit; E2 = month/sector/unit; E3 = month/reference-category/unit. Also flag a month/category occurring under multiple units, rather than treating it as two valid independent observations.
- Exact repeated rows are duplicate candidates, not evidence of additional activity. Keep both raw records, flag them, and block the affected analytical key. A later exclusion is allowed only through a documented review decision retaining the original row references and chosen resolution. No automatic `drop_duplicates` or addition of repeated values is approved.
- When the same key has different values, quarantine the affected key for investigation. Do not choose the largest, newest-looking, first, or last row without source/revision evidence.
- Matching keys across different snapshot hashes are revision comparisons, not duplicates within one dataset. A release must declare its selected snapshot per resource and preserve previous revisions; never mix snapshots opportunistically by month to make totals match.
- Deferred DMF examples remain unchanged: March 2012 domestic supply is repeated, and a May BE 2548 Chakrawan production record is repeated. DMF production's candidate field/block key has not been proven unique; review its grain before any future deduplication.

## 7. Units and aggregation

- Treat EPPO MMSCFD as the publisher's reported daily gas rate, retaining the Myanmar 1,000 BTU/SCF qualification. Treat E3 values as percentages. Do not infer that equal unit labels establish equal cross-agency measurement boundaries.
- Unexpected units block aggregation. Do not silently normalise LNG tonnes, condensate barrels, LPG kilograms, or oil equivalents into gas volume. EPPO's LNG row already uses MMSCFD; no new LNG conversion is needed.
- Sum compatible source components **within a month**, once each. Never add their subtotal or total rows back into that sum. E1 and E2 are separate facts; aggregate each before comparison to avoid multiplying records in a many-to-many join.
- Compute the selected KPI formulas only from complete, reviewed inputs. A zero or unavailable denominator gives “not available”, not zero percent or infinity. An explicit zero numerator with a positive valid denominator may produce zero percent.
- Never label a sum of monthly daily rates as annual volume. Annual average rates use calendar-day weights only after confirming the calendar-day averaging basis; require all twelve valid months and retain leap days. Until that basis is confirmed, withhold derived annual rates and volumes rather than assume it. Recompute multi-month shares from compatible weighted components, not an average of rounded percentages.
- Do not use DMF `DAYSOFPRODUCE` as a calendar-day multiplier. No gas-volume/energy/mass conversions are implemented or approved in this rules document.

## 8. Reconciliation and tolerances

These are **project validation policies**, not publisher-certified tolerances or explanations for differences. A tolerance never authorises changing a source value.

| Comparison | Rule and consequence |
| --- | --- |
| Parsed component versus its selected raw CSV record | Exact numeric agreement, including an explicit zero. Any difference is an error; no tolerance. |
| Derived total versus sum of its selected validated components | Exact arithmetic equality at calculation precision. Numerical implementation precision must be documented later; no blanket one-unit allowance. |
| Displayed four-sector shares | Must sum to 100% within 0.1 percentage point, consistent with AC5, only when all four valid inputs exist. Calculate shares before display rounding. |
| Calculated LNG share of imports versus E3 | Absolute difference at most 0.1 percentage point for each of the 132 reporting months (AC6). Larger differences or unavailable comparisons fail the baseline check and require review. Do not overwrite either series to force agreement. |
| E3 LNG plus MYANMAR shares | Must sum to 100% within 0.1 percentage point, with both categories present, finite, and within range. This does not validate import dependence's total-supply denominator. |
| Sum of rounded CSV components versus separately published workbook subtotal | Record the signed difference, month, units, component count, and both snapshot hashes. Exact agreement passes this comparison only. Any nonzero difference requires review; do not declare it a calculation error or confirmed rounding automatically. |

For the last comparison, a diagnostic rounding envelope may be used **only if** matching series/snapshot basis and rounding to nearest are established: `0.5 × (sum(component reporting increments) + subtotal reporting increment)`. With `n` components and one subtotal all rounded to whole MMSCFD, that is `(n + 1) / 2` MMSCFD. This is an arithmetic bound under stated assumptions, not an unconditional acceptance threshold. Being inside it means “consistent with rounding”; it does not prove rounding caused the difference. Outside it requires investigation of revisions, units, boundaries, mapping, or missing components. If assumptions are unverified, the comparison remains unresolved. Any release exception needs a documented explanation and must remain visible in quality reporting.

The recorded January 2025 import comparison is an actual assessment finding: CSV components sum to 1,489 MMSCFD, while the workbook subtotal is 1,490. Under this policy it remains a review item, not an approved correction. Do not turn this example into a rule that every one-unit difference is acceptable.

DMF versus EPPO is a definition/boundary investigation, not an equality test with an arbitrary tolerance. Supply versus sector consumption is also not an enforced equality or evidence of a shortage/surplus.

## 9. Quality decisions and release gates

Use three outcomes in a later validation report:

- **Pass:** the specified check was run against identified inputs and met the rule.
- **Review:** evidence or interpretation is unresolved. Do not claim the affected KPI is validated; a visible warning is not permission to publish an incomplete total.
- **Fail:** a known rule is violated. Withhold affected rows/keys or dependent KPIs from the validated reporting layer while retaining the raw evidence.

For every review/failure, record rule ID or section, snapshot hash, original row/key or missing expected key, observed issue, affected KPI/period, and any resolution evidence. Human decisions must be dated and attributable; do not invent approvals. Rules and applicability mappings need versions so later reruns can reproduce a decision.

Before release, demonstrate AC1–AC10 from [business requirements](business_requirements.md#acceptance-criteria-for-a-later-implementation), including complete scope coverage, sampled source checks, all-month import-share validation, and traceable unresolved issues. Passing a file parser or counting 132 months is not proof that all components or KPIs are correct. Do not silently drop bad months and label the remainder a complete year.

## 10. Status and next step

Step 4 is complete as a **documentation task**. Applicability decisions, rounding-basis confirmation, numerical reconciliation, and executable validation remain pending. No data was cleaned, converted, deleted, or loaded, and no validation pipeline was built. Step 5 is to design the warehouse using these rules; it requires a separate prompt.
