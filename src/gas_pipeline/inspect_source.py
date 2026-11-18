"""Read-only inspection of retained EPPO gas CSV snapshots; no data loading."""

import argparse
from collections import Counter
import csv
from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import io
import json
from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_PATH = PROJECT_ROOT / "data/raw/source_assessment/eppo_supply.csv"
REPORT_PATH = PROJECT_ROOT / "outputs/validation/eppo_supply_inspection.json"
EXPECTED_HASH = "cf57ec62948aedc61546b26c76d29d823b1b5e10a829c2269f1dd8d2000ab4e4"
EXPECTED_COLUMNS = ["Year", "Month", "Source", "Quantity", "UNIT"]
MONTH_NUMBERS = {
    name: number for number, name in enumerate(
        ("January", "February", "March", "April", "May", "June",
         "July", "August", "September", "October", "November", "December"), 1
    )
}
ALLOWED_SOURCES = {
    "ERAWAN", "BONGKOT", "BONGKOT TAI", "PAILIN", "ARTHIT", "TANTAWAN",
    "PHU HORM", "SIRIKIT", "LANTA", "NAM PHONG", "JASMINE", "YOONG THONG",
    "JDA", "OTHERS", "YADANA", "YETAKUN", "ZAWTIKA", "LNG",
}
EXPECTED_MONTHS = {
    date(year, month, 1) for year in range(2015, 2026) for month in range(1, 13)
}
CONSUMPTION_PATH = PROJECT_ROOT / "data/raw/source_assessment/eppo_consumption.csv"
CONSUMPTION_HASH = "7fddd2cb1f91916182bd4f45c869a64b62b8a4ff1bd047d67b58f573f8ea91e9"
CONSUMPTION_REPORT_PATH = PROJECT_ROOT / "outputs/validation/eppo_consumption_inspection.json"
ALLOWED_SECTORS = {"ELECTRICITY", "GSP", "INDUSTRY", "NGV"}
IMPORT_SHARE_PATH = PROJECT_ROOT / "data/raw/source_assessment/eppo_import_share.csv"
IMPORT_SHARE_HASH = "dc6bf80391bd742ddeaeb02658f3eb7768aaba00da2db99f7d351be6d815a050"
IMPORT_SHARE_REPORT_PATH = PROJECT_ROOT / "outputs/validation/eppo_import_share_inspection.json"
IMPORT_CATEGORIES = {"LNG", "MYANMAR"}


class InspectionFailure(Exception):
    """A known inspection rule failed."""


def inspect_supply(input_path=INPUT_PATH, expected_hash=EXPECTED_HASH):
    """Return evidence even on failure. Custom hashes support synthetic tests only."""
    return inspect_dataset(input_path, expected_hash, "supply")


def inspect_consumption(input_path=CONSUMPTION_PATH, expected_hash=CONSUMPTION_HASH):
    """Check sector consumption, including four-sector reporting-month coverage."""
    return inspect_dataset(input_path, expected_hash, "consumption")


def inspect_import_share(input_path=IMPORT_SHARE_PATH, expected_hash=IMPORT_SHARE_HASH):
    """Inspect published import-mix percentages, without converting gas rates."""
    return inspect_dataset(input_path, expected_hash, "import-share")


def inspect_dataset(input_path, expected_hash, dataset):
    is_share = dataset == "import-share"
    category_column = "Sector" if dataset == "consumption" else "Source"
    allowed_categories = {"supply": ALLOWED_SOURCES, "consumption": ALLOWED_SECTORS,
                          "import-share": IMPORT_CATEGORIES}[dataset]
    value_column = "Share" if is_share else "Quantity"
    expected_unit = "%" if is_share else "MMSCFD"
    value_rule = "share" if is_share else "quantity"
    expected_columns = ["Year", "Month", category_column, value_column, "UNIT"]
    input_path = Path(input_path)
    report = {
        "dataset": dataset,
        "inspection_time_utc": datetime.now(timezone.utc).isoformat(),
        "input_path": str(input_path.resolve()),
        "expected_sha256": expected_hash,
        "actual_sha256": None,
        "checker_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "rule_version": f"eppo-{dataset}-inspection-v2",
        "value_column": value_column,
        "unit": expected_unit,
        "status": "FAIL",
        "checks": {},
        "issues": [],
        "summary": {},
        "not_run": [
            ("Monthly source applicability / component completeness" if dataset == "supply"
             else "Manual reconciliation with official reference values"),
            "Workbook subtotal and import-share reconciliation",
            "KPI calculations, database loading",
        ],
        "qualification": "Inspection only; not acceptance for KPI publication. Counts on failure may be partial.",
    }
    row_number = None
    reader = None

    def check(rule, condition, message):
        report["checks"][rule] = "PASS" if condition else "FAIL"
        if not condition:
            report["issues"].append({
                "rule": rule, "record_number": row_number,
                "csv_line_end": reader.line_num if reader else None,
                "message": message,
            })
            raise InspectionFailure(message)

    try:
        raw_bytes = input_path.read_bytes()
    except OSError as error:
        report["checks"]["file_read"] = "FAIL"
        report["issues"].append({"rule": "file_read", "message": str(error)})
        return report

    report["checks"]["file_read"] = "PASS"
    report["actual_sha256"] = hashlib.sha256(raw_bytes).hexdigest()
    scope_counts = Counter({"reporting": 0, "support_2014": 0, "outside_scope": 0})
    month_counts = Counter()
    seen_records = {}
    scales = Counter()
    quantities = []
    observed_months = set()
    sectors_by_month = {}
    shares_by_month = {}
    row_count = 0
    try:
        check("fingerprint", report["actual_sha256"] == expected_hash,
              "File differs from the expected snapshot; review the revision.")
        text = raw_bytes.decode("utf-8-sig")
        report["checks"]["encoding"] = "PASS"
        reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
        check("columns", reader.fieldnames == expected_columns,
              f"Expected {expected_columns}; received {reader.fieldnames}.")
        for row_number, row in enumerate(reader, 1):
            row_count = row_number
            check("record_structure", None not in row and None not in row.values(),
                  "Record has extra or missing fields.")
            check("nonblank_values", all(value.strip() for value in row.values()),
                  "Record contains a blank field.")
            # Do not silently standardise source text in this inspection.
            check("outer_whitespace", all(value == value.strip() for value in row.values()),
                  "Outer whitespace requires an explicit standardisation decision.")
            check(f"{value_rule}_notation", re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", row[value_column]) is not None,
                  f"{value_column} must be a nonnegative plain decimal, not NaN, infinity or scientific notation.")
            quantity = Decimal(row[value_column])
            scale = max(0, -quantity.as_tuple().exponent)
            check(f"{value_rule}_storage_fit", scale <= 6 and quantity < Decimal("1000000000000"),
                  f"{value_column} exceeds proposed DECIMAL(18,6) range or scale; no rounding applied.")
            if is_share:
                check("share_range", quantity <= 100, "Share must be between 0 and 100 percent.")
            check("unit", row["UNIT"] == expected_unit, f"Expected unit {expected_unit}.")
            check("year", re.fullmatch(r"[0-9]{4}", row["Year"]) is not None,
                  "Year must contain four Gregorian digits.")
            check("month", row["Month"] in MONTH_NUMBERS, "Unknown English month name.")
            check("year_range", 1 <= int(row["Year"]) <= 9999, "Year is outside the calendar range.")
            observation_month = date(int(row["Year"]), MONTH_NUMBERS[row["Month"]], 1)
            check("snapshot_dates", date(2000 if is_share else 1986, 1, 1) <= observation_month <= date(2026, 7, 1),
                  "Date is outside the assessed snapshot range.")
            check("sector" if dataset == "consumption" else "source",
                  row[category_column] in allowed_categories,
                  f"Unknown {category_column} label.")
            record_key = (observation_month, row[category_column], row["UNIT"])
            check("duplicate_key", record_key not in seen_records,
                  f"Repeated month/{category_column}/unit {record_key!r}; first record {seen_records.get(record_key)}.")
            seen_records[record_key] = row_number
            observed_months.add(observation_month)
            quantities.append(quantity)
            scales[scale] += 1
            if observation_month in EXPECTED_MONTHS:
                scope_counts["reporting"] += 1
                month_counts[observation_month.isoformat()[:7]] += 1
                if dataset == "consumption":
                    sectors_by_month.setdefault(observation_month, set()).add(row["Sector"])
                if is_share:
                    shares_by_month.setdefault(observation_month, {})[row["Source"]] = quantity
            elif observation_month.year == 2014:
                scope_counts["support_2014"] += 1
            else:
                scope_counts["outside_scope"] += 1

        missing_months = sorted(EXPECTED_MONTHS - observed_months)
        report["summary"]["missing_reporting_months"] = [m.isoformat()[:7] for m in missing_months]
        check("reporting_month_coverage", not missing_months,
              f"Missing reporting months: {report['summary']['missing_reporting_months']}.")
        if dataset == "consumption":
            missing_sectors = {
                month.isoformat()[:7]: sorted(ALLOWED_SECTORS - sectors_by_month.get(month, set()))
                for month in sorted(EXPECTED_MONTHS)
                if sectors_by_month.get(month, set()) != ALLOWED_SECTORS
            }
            report["summary"]["missing_reporting_sectors"] = missing_sectors
            check("reporting_sector_completeness", not missing_sectors,
                  f"Missing reporting-month sectors: {missing_sectors}.")
        if is_share:
            missing_categories = {
                month.isoformat()[:7]: sorted(IMPORT_CATEGORIES - shares_by_month.get(month, {}).keys())
                for month in sorted(EXPECTED_MONTHS)
                if set(shares_by_month.get(month, {})) != IMPORT_CATEGORIES
            }
            report["summary"]["missing_reporting_categories"] = missing_categories
            check("reporting_import_category_completeness", not missing_categories,
                  f"Missing reporting-month import categories: {missing_categories}.")
            sums = {month.isoformat()[:7]: sum(values.values(), Decimal("0"))
                    for month, values in sorted(shares_by_month.items())}
            report["summary"]["reporting_share_totals"] = {month: str(total) for month, total in sums.items()}
            report["summary"]["share_total_tolerance_percentage_points"] = "0.1"
            bad_sums = {month: str(total) for month, total in sums.items()
                        if abs(total - Decimal("100")) > Decimal("0.1")}
            check("reporting_share_sum", not bad_sums,
                  f"Monthly import shares differ from 100% by more than 0.1 percentage point: {bad_sums}.")
        report["status"] = "PASS"
    except InspectionFailure:
        pass
    except (UnicodeError, csv.Error) as error:
        rule = "encoding" if isinstance(error, UnicodeError) else "csv_parse"
        report["checks"][rule] = "FAIL"
        report["issues"].append({"rule": rule, "record_number": row_number,
                                 "csv_line_end": reader.line_num if reader else None,
                                 "message": str(error)})
    finally:
        report["summary"].update({
            "records_read": row_count,
            "validated_records": len(seen_records),
            "scope_counts": dict(scope_counts),
            "reporting_months_present": len(month_counts),
            "reporting_month_counts": dict(sorted(month_counts.items())),
            "minimum_records_per_reporting_month": min(month_counts.values(), default=None),
            "maximum_records_per_reporting_month": max(month_counts.values(), default=None),
            "first_observation": min(observed_months).isoformat() if observed_months else None,
            "last_observation": max(observed_months).isoformat() if observed_months else None,
            f"{value_rule}_min": str(min(quantities)) if quantities else None,
            f"{value_rule}_max": str(max(quantities)) if quantities else None,
            f"{value_rule}_decimal_places_counts": dict(sorted(scales.items())),
        })
        try:
            unchanged = hashlib.sha256(input_path.read_bytes()).hexdigest() == report["actual_sha256"]
        except OSError:
            unchanged = False
        report["checks"]["input_unchanged"] = "PASS" if unchanged else "FAIL"
        if not unchanged:
            report["status"] = "FAIL"
            report["issues"].append({"rule": "input_unchanged", "message": "Input changed or became unreadable during inspection."})
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=("supply", "consumption", "import-share"), default="supply")
    parser.add_argument("--input", type=Path)
    args = parser.parse_args()
    default_input, report_path, inspect = {
        "supply": (INPUT_PATH, REPORT_PATH, inspect_supply),
        "consumption": (CONSUMPTION_PATH, CONSUMPTION_REPORT_PATH, inspect_consumption),
        "import-share": (IMPORT_SHARE_PATH, IMPORT_SHARE_REPORT_PATH, inspect_import_share),
    }[args.dataset]
    input_path = args.input or default_input
    # Always write to the ignored output folder, never to the input path.
    if input_path.resolve() == report_path.resolve():
        parser.error("Input cannot be the report output path.")
    report = inspect(input_path)
    try:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    except OSError as error:
        print(f"FAIL: Could not save validation report: {error}")
        return 1
    print(f"{args.dataset.title()} inspection: {report['status']}")
    for name, outcome in report["checks"].items():
        print(f"  {name}: {outcome}")
    print("Counts:", report["summary"].get("scope_counts", {}))
    print("Report:", report_path)
    for issue in report["issues"]:
        print("Issue:", issue)
    print(report["qualification"])
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
