"""Compare LNG's calculated share of imports with EPPO's published reference."""

from collections import Counter
import csv
from datetime import date, datetime, timezone
from decimal import Decimal, localcontext
import hashlib
import io
import json
from pathlib import Path

import inspect_source as source

REPORT_PATH = source.PROJECT_ROOT / "outputs/validation/import_share_comparison.json"
PIPELINE_SOURCES = ("YADANA", "YETAKUN", "ZAWTIKA")
REQUIRED_SOURCES = ("LNG",) + PIPELINE_SOURCES
TOLERANCE = Decimal("0.1")


def compare_month(month, supply, reference):
    """Missing observations remain unavailable; never fill them with zero."""
    result = {"month": month.isoformat()[:7], "status": "REVIEW",
              "calculated_lng_share_percent": None,
              "published_lng_share_percent": str(reference["LNG"]) if "LNG" in reference else None,
              "difference_percentage_points": None}
    missing_supply = [name for name in REQUIRED_SOURCES if name not in supply]
    missing_reference = [name for name in source.IMPORT_CATEGORIES if name not in reference]
    if missing_supply or missing_reference:
        result.update(reason="Missing required observations", missing_supply=missing_supply,
                      missing_reference=sorted(missing_reference))
        return result
    with localcontext() as context:
        context.prec = 50
        pipeline = sum((supply[name] for name in PIPELINE_SOURCES), Decimal("0"))
        total = pipeline + supply["LNG"]
        result.update(lng_rate_mmscfd=str(supply["LNG"]), pipeline_rate_mmscfd=str(pipeline),
                      total_import_rate_mmscfd=str(total),
                      published_lng_share_percent=str(reference["LNG"]))
        if total <= 0:
            result["reason"] = "Nonpositive import denominator; percentage unavailable"
            return result
        calculated = supply["LNG"] / total * 100
        difference = calculated - reference["LNG"]
        result.update(calculated_lng_share_percent=str(calculated),
                      difference_percentage_points=str(difference),
                      status="PASS" if abs(difference) <= TOLERANCE else "FAIL")
    return result


def read_checked(path, inspection, value_column):
    """Read only the bytes identified by the just-completed inspection."""
    content = path.read_bytes()
    if hashlib.sha256(content).hexdigest() != inspection["actual_sha256"]:
        raise ValueError("Input changed between inspection and comparison")
    result = {}
    for number, row in enumerate(csv.DictReader(io.StringIO(content.decode("utf-8-sig"))), 1):
        month = date(int(row["Year"]), source.MONTH_NUMBERS[row["Month"]], 1)
        if month in source.EXPECTED_MONTHS:
            result.setdefault(month, {})[row["Source"]] = (Decimal(row[value_column]), number)
    return result


def run_comparison():
    report = {
        "inspection_time_utc": datetime.now(timezone.utc).isoformat(),
        "rule_version": "lng-import-share-comparison-v1",
        "checker_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "tolerance_percentage_points": str(TOLERANCE),
        "arithmetic": "Decimal, 50 significant digits; no display rounding before comparison",
        "formula": "100 * LNG / (LNG + YADANA + YETAKUN + ZAWTIKA)",
        "status": "FAIL", "months": [], "issues": [],
        "not_run": ["Total national supply completeness / denominator validation",
                    "Workbook subtotal reconciliation", "KPI publication acceptance"],
    }
    inspections = {"supply": source.inspect_supply(), "import_share": source.inspect_import_share()}
    report["input_inspections"] = inspections
    if any(item["status"] != "PASS" for item in inspections.values()):
        report["issues"].append("Comparison not run: an input inspection failed.")
        return report
    try:
        supply = read_checked(source.INPUT_PATH, inspections["supply"], "Quantity")
        reference = read_checked(source.IMPORT_SHARE_PATH, inspections["import_share"], "Share")
        for month in sorted(source.EXPECTED_MONTHS):
            supply_rows = supply.get(month, {})
            reference_rows = reference.get(month, {})
            result = compare_month(month, {key: value[0] for key, value in supply_rows.items()},
                                   {key: value[0] for key, value in reference_rows.items()})
            result["supply_record_numbers"] = {key: supply_rows[key][1] for key in REQUIRED_SOURCES if key in supply_rows}
            result["reference_record_numbers"] = {key: value[1] for key, value in reference_rows.items()}
            report["months"].append(result)
        counts = Counter(row["status"] for row in report["months"])
        differences = [Decimal(row["difference_percentage_points"]).copy_abs()
                       for row in report["months"] if row["difference_percentage_points"] is not None]
        report["summary"] = {"months": len(report["months"]),
                             "pass": counts["PASS"], "fail": counts["FAIL"], "review": counts["REVIEW"],
                             "maximum_absolute_difference_percentage_points": str(max(differences)) if differences else None}
        report["status"] = "FAIL" if counts["FAIL"] else "REVIEW" if counts["REVIEW"] else "PASS"
        for name, path in [("supply", source.INPUT_PATH), ("import_share", source.IMPORT_SHARE_PATH)]:
            if hashlib.sha256(path.read_bytes()).hexdigest() != inspections[name]["actual_sha256"]:
                raise ValueError(f"{name} input changed during comparison")
        report["inputs_unchanged"] = True
    except (OSError, ValueError) as error:
        report["status"] = "FAIL"
        report["issues"].append(str(error))
    return report


def main():
    report = run_comparison()
    try:
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    except OSError as error:
        print(f"FAIL: Could not save comparison report: {error}")
        return 1
    print("LNG import-share comparison:", report["status"])
    print("Summary:", report.get("summary", {}))
    print("Report:", REPORT_PATH)
    print("This validates import mix only, not import dependence or total supply completeness.")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
