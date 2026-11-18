"""Synthetic fixtures only: no downloaded source rows are stored here."""
import csv
import hashlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest

MODULE_PATH = Path(__file__).resolve().parents[1] / "src/gas_pipeline/inspect_source.py"
spec = importlib.util.spec_from_file_location("inspect_source", MODULE_PATH)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


def synthetic_rows():
    return [[str(year), month, "LNG", "1.25", "MMSCFD"]
            for year in range(2015, 2026) for month in checker.MONTH_NUMBERS]


def encode_rows(rows, headers=None):
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(checker.EXPECTED_COLUMNS if headers is None else headers)
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


class SupplyInspectionTests(unittest.TestCase):
    def inspect_bytes(self, content, expected_hash=None):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "synthetic.csv"
            path.write_bytes(content)
            result = checker.inspect_supply(path, expected_hash or hashlib.sha256(content).hexdigest())
            self.assertEqual(path.read_bytes(), content)
            return result

    def assert_failed(self, result, rule):
        self.assertEqual(result["status"], "FAIL")
        self.assertIn(rule, [issue["rule"] for issue in result["issues"]])

    def test_valid_synthetic_input_and_scope_counts(self):
        rows = synthetic_rows() + [["2014", "January", "LNG", "0", "MMSCFD"],
                                   ["2026", "January", "LNG", "2", "MMSCFD"]]
        result = self.inspect_bytes(b"\xef\xbb\xbf" + encode_rows(rows))
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["summary"]["scope_counts"],
                         {"reporting": 132, "support_2014": 1, "outside_scope": 1})
        self.assertEqual(result["summary"]["reporting_months_present"], 132)
        self.assertTrue(result["not_run"])

    def test_missing_file(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assert_failed(checker.inspect_supply(Path(folder) / "absent.csv"), "file_read")

    def test_changed_fingerprint(self):
        self.assert_failed(self.inspect_bytes(encode_rows(synthetic_rows()), "0" * 64), "fingerprint")

    def test_headers(self):
        for headers in [[], ["Year", "Year", "Source", "Quantity", "UNIT"],
                        checker.EXPECTED_COLUMNS + ["Extra"]]:
            with self.subTest(headers=headers):
                self.assert_failed(self.inspect_bytes(encode_rows(synthetic_rows(), headers)), "columns")

    def test_bad_record_values(self):
        cases = [
            (3, "", "nonblank_values"), (3, "abc", "quantity_notation"),
            (3, "NaN", "quantity_notation"), (3, "Infinity", "quantity_notation"),
            (3, "-1", "quantity_notation"), (3, "1e3", "quantity_notation"),
            (3, "0.0000001", "quantity_storage_fit"),
            (3, "1000000000000", "quantity_storage_fit"),
            (4, "tonnes", "unit"), (0, "0000", "year_range"),
            (0, "20xx", "year"), (1, "Jan", "month"),
            (0, "2027", "snapshot_dates"), (2, "UNKNOWN", "source"),
            (2, " LNG", "outer_whitespace"),
        ]
        for column, value, rule in cases:
            with self.subTest(value=value, rule=rule):
                rows = synthetic_rows()
                rows[0][column] = value
                self.assert_failed(self.inspect_bytes(encode_rows(rows)), rule)

    def test_record_width(self):
        for row in [["2015", "January"], ["2015", "January", "LNG", "1", "MMSCFD", "extra"]]:
            with self.subTest(row=row):
                self.assert_failed(self.inspect_bytes(encode_rows([row])), "record_structure")

    def test_duplicate_key(self):
        rows = synthetic_rows()
        rows.append(rows[0].copy())
        result = self.inspect_bytes(encode_rows(rows))
        self.assert_failed(result, "duplicate_key")
        self.assertEqual(result["issues"][0]["record_number"], 133)

    def test_missing_month(self):
        result = self.inspect_bytes(encode_rows(synthetic_rows()[1:]))
        self.assert_failed(result, "reporting_month_coverage")
        self.assertEqual(result["summary"]["missing_reporting_months"], ["2015-01"])

    def test_empty_and_invalid_encoding(self):
        self.assert_failed(self.inspect_bytes(b""), "columns")
        self.assert_failed(self.inspect_bytes(b"\xff"), "encoding")
        self.assert_failed(self.inspect_bytes(encode_rows([])), "reporting_month_coverage")

    def test_malformed_csv(self):
        content = b'Year,Month,Source,Quantity,UNIT\n2015,January,"LNG,1,MMSCFD\n'
        self.assert_failed(self.inspect_bytes(content), "csv_parse")


class ConsumptionInspectionTests(unittest.TestCase):
    def rows(self):
        return [[str(year), month, sector, "1.25", "MMSCFD"]
                for year in range(2015, 2026) for month in checker.MONTH_NUMBERS
                for sector in sorted(checker.ALLOWED_SECTORS)]

    def inspect_rows(self, rows, headers=None):
        content = encode_rows(rows, headers or ["Year", "Month", "Sector", "Quantity", "UNIT"])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "synthetic_consumption.csv"
            path.write_bytes(content)
            report = checker.inspect_consumption(path, hashlib.sha256(content).hexdigest())
            self.assertEqual(path.read_bytes(), content)
            return report

    def test_complete_reporting_sectors_with_sparse_earlier_history(self):
        rows = self.rows() + [["2014", "January", "ELECTRICITY", "0", "MMSCFD"]]
        report = self.inspect_rows(rows)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["dataset"], "consumption")
        self.assertEqual(report["summary"]["scope_counts"]["reporting"], 528)
        self.assertEqual(report["summary"]["minimum_records_per_reporting_month"], 4)
        self.assertEqual(report["summary"]["missing_reporting_sectors"], {})

    def test_missing_one_sector_is_not_missing_month(self):
        report = self.inspect_rows(self.rows()[1:])
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["checks"]["reporting_month_coverage"], "PASS")
        self.assertEqual(report["checks"]["reporting_sector_completeness"], "FAIL")
        self.assertEqual(report["summary"]["missing_reporting_sectors"], {"2015-01": ["ELECTRICITY"]})

    def test_invalid_sector_and_shared_value_checks(self):
        for column, value, rule in [(2, "LNG", "sector"), (3, "-1", "quantity_notation"),
                                    (4, "tonnes", "unit")]:
            with self.subTest(rule=rule):
                rows = self.rows()
                rows[0][column] = value
                report = self.inspect_rows(rows)
                self.assertEqual(report["status"], "FAIL")
                self.assertEqual(report["issues"][0]["rule"], rule)

    def test_duplicate_sector_key(self):
        rows = self.rows()
        rows.append(rows[0].copy())
        report = self.inspect_rows(rows)
        self.assertEqual(report["issues"][0]["rule"], "duplicate_key")
        self.assertEqual(report["issues"][0]["record_number"], 529)

    def test_supply_header_is_rejected(self):
        report = self.inspect_rows(self.rows(), checker.EXPECTED_COLUMNS)
        self.assertEqual(report["issues"][0]["rule"], "columns")


class ImportShareInspectionTests(unittest.TestCase):
    def rows(self, lng="40", myanmar="60"):
        return [[str(year), month, category, value, "%"]
                for year in range(2015, 2026) for month in checker.MONTH_NUMBERS
                for category, value in [("LNG", lng), ("MYANMAR", myanmar)]]

    def inspect_rows(self, rows):
        content = encode_rows(rows, ["Year", "Month", "Source", "Share", "UNIT"])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "synthetic_import_share.csv"
            path.write_bytes(content)
            report = checker.inspect_import_share(path, hashlib.sha256(content).hexdigest())
            self.assertEqual(path.read_bytes(), content)
            return report

    def test_valid_shares_and_zero_endpoint(self):
        for lng, myanmar in [("40", "60"), ("0", "100")]:
            with self.subTest(lng=lng):
                report = self.inspect_rows(self.rows(lng, myanmar))
                self.assertEqual(report["status"], "PASS")
                self.assertEqual(report["summary"]["scope_counts"]["reporting"], 264)
                self.assertEqual(report["summary"]["reporting_months_present"], 132)
                self.assertEqual(report["unit"], "%")

    def test_sum_tolerance_boundary(self):
        for myanmar, outcome in [("60.1", "PASS"), ("59.9", "PASS"),
                                 ("60.100001", "FAIL"), ("59.899999", "FAIL")]:
            with self.subTest(myanmar=myanmar):
                report = self.inspect_rows(self.rows("40", myanmar))
                self.assertEqual(report["status"], outcome)
                self.assertEqual(report["checks"]["reporting_share_sum"], outcome)

    def test_missing_category(self):
        report = self.inspect_rows(self.rows()[1:])
        self.assertEqual(report["checks"]["reporting_month_coverage"], "PASS")
        self.assertEqual(report["issues"][0]["rule"], "reporting_import_category_completeness")
        self.assertEqual(report["summary"]["missing_reporting_categories"], {"2015-01": ["LNG"]})

    def test_invalid_values_categories_units_and_dates(self):
        for column, value, rule in [(3, "100.01", "share_range"), (3, "-1", "share_notation"),
                                    (3, "NaN", "share_notation"), (4, "MMSCFD", "unit"),
                                    (2, "YADANA", "source"), (0, "1999", "snapshot_dates")]:
            with self.subTest(value=value):
                rows = self.rows()
                rows[0][column] = value
                report = self.inspect_rows(rows)
                self.assertEqual(report["status"], "FAIL")
                self.assertEqual(report["issues"][0]["rule"], rule)

    def test_duplicate_and_missing_month(self):
        rows = self.rows()
        report = self.inspect_rows(rows + [rows[0]])
        self.assertEqual(report["issues"][0]["rule"], "duplicate_key")
        report = self.inspect_rows(rows[2:])
        self.assertEqual(report["issues"][0]["rule"], "reporting_month_coverage")


if __name__ == "__main__":
    unittest.main()
