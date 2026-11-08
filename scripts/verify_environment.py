"""Smoke-test the retail analytics stack using temporary synthetic data."""

import tempfile
from pathlib import Path

import duckdb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import nbformat
import numpy as np
import pandas as pd
import seaborn as sns
from nbconvert.preprocessors import ExecutePreprocessor
from sqlalchemy import create_engine


def main():
    sales = pd.DataFrame({"store": ["A", "A", "B"], "units": [2, 3, 4]})
    with tempfile.TemporaryDirectory(prefix="retail-analytics-") as directory:
        root = Path(directory)
        with duckdb.connect() as connection:
            connection.register("sales", sales)
            total = connection.sql("SELECT SUM(units) FROM sales").fetchone()[0]
        assert total == 9
        engine = create_engine("sqlite://")
        try:
            sales.to_sql("sales", engine, index=False)
            result = pd.read_sql("SELECT SUM(units) AS total FROM sales", engine)
            assert result.loc[0, "total"] == 9
        finally:
            engine.dispose()
        for extension in ("parquet", "xlsx"):
            path = root / f"sales.{extension}"
            if extension == "parquet":
                sales.to_parquet(path, index=False)
                restored = pd.read_parquet(path)
            else:
                sales.to_excel(path, index=False)
                restored = pd.read_excel(path)
            pd.testing.assert_frame_equal(sales, restored)
        assert np.sum(sales["units"].to_numpy()) == 9
        sns.barplot(data=sales, x="store", y="units", errorbar=None)
        plt.savefig(root / "sales.png")
        plt.close("all")
        notebook = nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell(
            "import pandas as pd, duckdb\n"
            "sales = pd.DataFrame({'units': [2, 3, 4]})\n"
            "with duckdb.connect() as con:\n"
            "    con.register('sales', sales)\n"
            "    assert con.sql('SELECT SUM(units) FROM sales').fetchone()[0] == 9\n"
            "print('Notebook SQL passed')"
        )])
        ExecutePreprocessor(timeout=120, kernel_name="python3").preprocess(
            notebook, {"metadata": {"path": directory}}
        )
        assert "Notebook SQL passed" in notebook.cells[0].outputs[0].text
    print("PASS: dataframe SQL, SQLite, Excel, Parquet, plots, and Jupyter execution")


if __name__ == "__main__":
    main()
