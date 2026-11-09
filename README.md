# Thailand Natural Gas Supply & Demand: A Data Warehouse and BI Dashboard

An independent portfolio project for a PTT data analyst internship, using official public Thai energy statistics. It is not an official PTT product.

The project is currently in requirements and source assessment. The proposed first scope is monthly national supply trends, import dependence, and consumption by sector for 2015–2025, with an optional partial-year extension through July 2026. No warehouse pipeline or dashboard has been built yet.

- [Business requirements, KPI definitions, and acceptance criteria](docs/business_requirements.md)
- [Verified sources, observed coverage, and feasibility recommendation](docs/source_assessment.md)

The Python, SQL, and Jupyter environment is ready for source exploration and the later warehouse and dashboard work.

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

Keep local inputs under `data/raw/`, prepared data under `data/processed/`, and exports under `outputs/`. These directories, local databases, notebook checkpoints, credentials, and virtual environments are ignored by Git. Source-assessment downloads are local only, under `data/raw/source_assessment/`. Do not commit raw downloads or notebook outputs containing source data. Never add LNG tonnes to gas volume; see the unit rules in the business requirements.

## Verify the installation

```bash
source .venv/bin/activate
python -m pip check
python -m jupyterlab --version
```

These commands check dependency compatibility and confirm that JupyterLab is installed. They do not validate source data or run a pipeline.
