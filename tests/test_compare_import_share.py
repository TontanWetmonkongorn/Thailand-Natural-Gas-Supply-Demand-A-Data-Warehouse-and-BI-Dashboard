"""Invented in-memory values test comparison behaviour; not source observations."""
from datetime import date
from decimal import Decimal
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src/gas_pipeline"))
import compare_import_share as comparison


class ImportComparisonTests(unittest.TestCase):
    def compare(self, published="60", **changes):
        supply = {"LNG": Decimal("600"), "YADANA": Decimal("200"),
                  "YETAKUN": Decimal("0"), "ZAWTIKA": Decimal("200")}
        supply.update(changes)
        return comparison.compare_month(date(2025, 1, 1), supply,
                                        {"LNG": Decimal(published), "MYANMAR": 100 - Decimal(published)})

    def test_agreement_and_signed_difference(self):
        result = self.compare("60.04")
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(Decimal(result["difference_percentage_points"]), Decimal("-0.04"))

    def test_tolerance_boundary_and_failure(self):
        for reference, outcome in [("60.1", "PASS"), ("59.9", "PASS"), ("60.100001", "FAIL")]:
            with self.subTest(reference=reference):
                self.assertEqual(self.compare(reference)["status"], outcome)

    def test_missing_is_not_zero(self):
        result = comparison.compare_month(date(2025, 1, 1), {"LNG": Decimal("1")}, {})
        self.assertEqual(result["status"], "REVIEW")
        self.assertIsNone(result["calculated_lng_share_percent"])
        self.assertIn("YETAKUN", result["missing_supply"])
        self.assertIn("LNG", result["missing_reference"])

    def test_zero_denominator(self):
        result = self.compare(LNG=Decimal("0"), YADANA=Decimal("0"), ZAWTIKA=Decimal("0"))
        self.assertEqual(result["status"], "REVIEW")
        self.assertIsNone(result["calculated_lng_share_percent"])


if __name__ == "__main__":
    unittest.main()
