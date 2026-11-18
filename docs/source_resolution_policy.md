# Source resolution policy: April 2021 YETAKUN

Policy ID: `YETAKUN-202104-EPPO-WORKBOOK-v1`
Recorded: 18 November 2026 (Asia/Bangkok)
Status: documented for a later implementation; not applied to data or comparison results.

## Purpose

A missing CSV record is not a reported zero. For this one observation, EPPO's
retained workbook supplies an explicit numeric zero. This policy defines how a
later process can expose that evidence without modifying the CSV or silently
mixing source versions. It does not authorise a general missing-to-zero rule.

The investigation and source URLs are in the
[source assessment](source_assessment.md#yetakun-missing-record-investigation--18-november-2026).
This is a project interpretation of evidence, not an EPPO missing-value rule or
a claim of independent human approval.

## Exact evidence and boundaries

| Item | Selected evidence |
| --- | --- |
| Observation | Gregorian month 2021-04-01; source YETAKUN; unit MMSCFD |
| Primary CSV snapshot | E1 `eppo_supply.csv`, SHA-256 `cf57ec62948aedc61546b26c76d29d823b1b5e10a829c2269f1dd8d2000ab4e4`; no corresponding record |
| Supplementary snapshot | EPPO Table 3.1-1M, `T03_01_01-1.xls`, SHA-256 `8b92ace2060438f3b84d6b80fce7b51edd3d2e34f5fcb781f937bddc21795cc0` |
| Official workbook URL | https://www.eppo.go.th/wp-content/uploads/2026/04/T03_01_01-1.xls |
| Locator | Sheet `tab38c`, numeric cell R502 = 0; row 498 establishes 2021, A502 is APR, R6 is Yetakun, row 3 states MMSCFD |
| Unit qualification | Preserve workbook note: Myanmar natural gas heat value = 1,000 BTU/SCF |
| Companion import observations | April YADANA 370, ZAWTIKA 233, LNG 822 MMSCFD match numerically in retained CSV and workbook Q502/S502/T502 |
| Excluded months | May and June 2021: workbook R503/R504 are blank, not numeric zero |

Companion agreement supports this limited supplement; it does not establish that
all revisions, source definitions or other months match. Never add the workbook's
Total Import subtotal to component values or force components to equal that subtotal.
The shutdown statements provide context, not replacement monthly measurements.

## Behaviour required before applying the policy

1. Verify both selected snapshot hashes. Missing evidence or changed bytes blocks
   this policy and triggers a new review; never fetch a newer file silently.
2. Verify the workbook sheet, year/month/source/unit headings, cell type and exact
   numeric value. A blank, text zero or changed heading must not pass this rule.
3. Confirm that April's E1 YETAKUN key is absent and that the three companion
   import values still match the cited cells. If the CSV contains an observation,
   preserve it and raise a revision/conflict review rather than inserting another.
4. Keep the original CSV and its inspection unchanged. Create an explicitly
   labelled supplementary observation in a separate interpretation only, carrying
   policy ID/version, both snapshot hashes, workbook sheet/cell, original key,
   value, unit, actual processing time and implementing code hash. No historic
   download timestamp or raw CSV record number may be invented for this value.
5. Preserve two comparison outcomes: the existing CSV-only result and a separately
   labelled result using this evidence. The latter must identify its supplementary
   observation; it must never be presented as a CSV-only pass. A future warehouse
   interpretation must link both inputs, not attribute the value to the CSV.
6. Do not create YETAKUN zero observations for May/June or any other key. Keep
   those calculations unavailable/REVIEW. Do not infer exact imports from rounded
   subtotals or infer zero imports merely from a production shutdown notice.

## Verification required for the later implementation

- Test successful extraction of the exact numeric cell and the companion checks.
- Test refusal for changed hashes, blank/text cells, wrong date/source/unit,
  conflicting existing CSV observations and mismatched companion values.
- Verify the supplementary comparison separately against E3 at the existing
  inclusive 0.1 percentage-point tolerance; do not assume the outcome in advance.
- Confirm May/June remain REVIEW, both raw files are unchanged, and the report
  distinguishes original and supplementary evidence.
- Record the applied policy version and result before changing any progress claim.

Until that implementation runs, the actual result remains **129 PASS / 3 REVIEW**.
Even if April later passes, full 132-month AC6 acceptance remains unmet while
May/June are unresolved. This policy does not validate total national supply,
import dependence, annual-rate assumptions or publication readiness.

## Next step

Implement and test this one supplement in a separate task, or proceed with a
separately requested Silver transformation retaining the current review flags.
Further policy versions must describe changed evidence and applicability rather
than silently expanding this exception to other observations.
