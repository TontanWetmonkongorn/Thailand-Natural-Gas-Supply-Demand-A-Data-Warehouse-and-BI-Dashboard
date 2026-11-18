"""Silver transformation tests use synthetic values, not downloaded data rows."""
from datetime import date
from decimal import Decimal
from pathlib import Path
import sys
import tempfile
import unittest

import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src/gas_pipeline"))
import transform_supply as transform


class SupplyTransformationTests(unittest.TestCase):
    def test_typed_values_original_text_and_quality_flags(self):
        content = (b'Year,Month,Source,Quantity,UNIT\n'
                   b'2014,January,LNG,0,MMSCFD\n'
                   b'2021,April,LNG,1.2500,MMSCFD\n'
                   b'2026,January,LNG,2,MMSCFD\n')
        table = transform.build_table(content, "synthetic-hash", {"2021-04": "REVIEW"})
        self.assertEqual(table.num_rows, 3)
        self.assertEqual(table.schema.field("quantity_mmscfd").type, pa.decimal128(18, 6))
        self.assertEqual(table.schema.field("month_start").type, pa.date32())
        rows = table.to_pylist()
        self.assertEqual(rows[1]["month_start"], date(2021, 4, 1))
        self.assertEqual(rows[1]["quantity_mmscfd"], Decimal("1.2500"))
        self.assertEqual(rows[1]["raw_quantity"], "1.2500")
        self.assertEqual(rows[0]["quantity_mmscfd"], Decimal("0"))
        self.assertEqual([r["scope"] for r in rows], ["support_2014", "reporting", "outside_scope"])
        self.assertEqual(rows[1]["import_mix_status"], "REVIEW")
        self.assertEqual(rows[0]["import_mix_status"], "NOT_CHECKED")
        self.assertTrue(all(r["source_completeness"] == "UNRESOLVED" for r in rows))
        self.assertEqual([r["source_record_number"] for r in rows], [1, 2, 3])
        # No missing YETAKUN row or numerical value is manufactured.
        self.assertEqual({r["source_code"] for r in rows}, {"LNG"})
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "table.parquet"
            pq.write_table(table, path)
            self.assertTrue(pq.read_table(path).equals(table))

    def test_invalid_input_does_not_create_silver_output(self):
        with tempfile.TemporaryDirectory() as folder:
            input_path = Path(folder) / "bad.csv"
            input_path.write_bytes(b'not the expected snapshot')
            output_root = Path(folder) / "silver"
            with self.assertRaisesRegex(ValueError, "Supply validation failed"):
                transform.transform_supply(input_path, output_root)
            self.assertFalse(output_root.exists())
            self.assertEqual(input_path.read_bytes(), b'not the expected snapshot')


if __name__ == "__main__":
    unittest.main()
