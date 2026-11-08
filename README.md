# Retail Performance & Demand Planning

Python, SQL, and Jupyter workspace for exploring retail sales and preparing demand plans.

## Setup

Use Python 3.11 or newer (initial setup verified with Python 3.14).

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

On Debian/Ubuntu, install the matching `python3-venv` package if virtual environment creation reports missing `ensurepip`.

## Work in notebooks

```bash
source .venv/bin/activate
python -m jupyterlab
```

In VS Code, select `.venv/bin/python` as the Python interpreter and notebook kernel. The environment includes ipykernel; no global kernel registration is required.

Use pandas and NumPy for preparation, DuckDB for SQL directly over dataframes, CSV, and Parquet, SQLAlchemy for database connections, openpyxl for Excel, and Matplotlib/Seaborn for charts. External databases may require an additional vendor driver.

## Data and outputs

Keep local inputs under `data/raw/`, prepared data under `data/processed/`, and exports under `outputs/`. These directories, local databases, notebook checkpoints, credentials, and `.venv/` are ignored by Git. Create the directories as needed; do not commit sensitive retail data or notebook outputs containing it.

## Verify the installation

```bash
source .venv/bin/activate
python -m pip check
python scripts/verify_environment.py
python -m jupyterlab --version
```

The verification script exercises dataframe SQL, SQLite through SQLAlchemy, Excel and Parquet round trips, plotting, and notebook execution using temporary synthetic data. It leaves no datasets in the repository.
