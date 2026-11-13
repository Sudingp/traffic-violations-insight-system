# 🚦 Traffic Violations Insight System: EDA, Cleaning & Interactive Streamlit Dashboard

A high-performance, enterprise-grade data engineering, exploratory analysis, and visualization system for large-scale traffic violation datasets (~2.07 million rows / 880 MB raw CSV).

---

## 📌 Project Overview & Objectives

Urban traffic safety agencies generate millions of enforcement records annually capturing details on violation types, driver demographics, vehicle specifications, location metadata, and accident severity. However, raw violation records are often noisy, inconsistent, duplicate-laden, and difficult to interpret without systematic data preprocessing.

This project delivers a complete end-to-end data pipeline that:
1. **Cleans & Preprocesses**: Standardizes heterogenous datetime formats, sanitizes GPS coordinates, normalizes 12 boolean flags, cleans vehicle makes/colors, and engineers temporal and severity features.
2. **Optimizes Data Storage**: Transforms raw 880 MB CSV into compressed Parquet storage (197 MB) and an indexed SQLite relational database (`traffic_violations.db`).
3. **Performs Structured EDA**: Answers key urban mobility questions using descriptive statistics and visual analytics.
4. **Delivers an Interactive Dashboard**: Powers a modern, responsive Streamlit web application with real-time dynamic filters, spatial heatmaps, KPI metrics, and a built-in SQL query engine.

---

## 🏗️ System Architecture

```
traffic-violation-system/
├── Traffic_Violations.csv                # Raw dataset (~2.07M rows / 880 MB)
├── src/                                  # Core Data Engineering Modules
│   ├── __init__.py
│   ├── preprocessing.py                  # Chunked ETL cleaning & feature engineering pipeline
│   ├── database.py                       # SQLite database manager & indexing engine
│   ├── api_client.py                     # Live feed client: paging, retries, backoff
│   ├── schema.py                         # Pydantic validation + feed-to-CSV field mapping
│   ├── live_ingest.py                    # Incremental, idempotent ingestion job (CLI)
│   ├── spark_preprocessing.py            # Same cleaning rules in PySpark (built-in functions, no UDFs)
│   ├── quality.py                        # Data-quality gate run before anything is published
│   ├── parity.py                         # Proves the pandas and Spark outputs are identical
│   ├── pipeline_tasks.py                 # The steps the Airflow DAGs run (unit-tested without Airflow)
│   └── logging_setup.py                  # Console + rotating file logs
├── dags/traffic_pipeline.py              # Airflow DAGs: bulk Spark ETL + daily live ingest
├── Dockerfile, docker-compose.yml        # Local Airflow + Spark in one container
├── data/                                 # Processed High-Performance Storage
│   ├── cleaned_traffic_violations.parquet # Compressed Parquet dataset (197 MB)
│   └── traffic_violations.db             # Indexed SQLite relational database
├── eda/                                  # Exploratory Data Analysis & Visualizations
│   ├── generate_eda.py                   # Automated chart generation script
│   ├── eda_report.md                     # Markdown EDA analytical report
│   └── charts/                           # High-res exported visual figures (Q1-Q6)
├── tests/                                # Automated Unit Test Suite
│   ├── test_preprocessing.py             # Preprocessing & type conversion tests
│   └── test_database.py                  # Database & KPI query tests
├── scripts/                              # Benchmark, sample-data generator, Task Scheduler wrapper
├── .github/workflows/tests.yml           # CI: pytest on every push
├── INCIDENTS.md                          # Incident log (root cause + fix + regression test)
├── app.py                                # Interactive Streamlit Dashboard App
├── requirements.txt                      # Project dependencies
└── README.md                             # Comprehensive project documentation
```

---

## 🛠️ Data Preprocessing & Cleaning Rules

All 43 dataset columns are rigorously cleaned and normalized:

| Column(s) | Cleaning & Normalization Strategy |
| :--- | :--- |
| `SeqID` | Unique stop UUID identifier. Exact row duplicates removed; multi-charge stops tracked via `Is_Multi_Charge`. |
| `Date Of Stop` & `Time Of Stop` | Formatted into ISO `Datetime_Of_Stop`. Gaps, future dates (>2026), and format glitches (`23.11.00` $\rightarrow$ `23:11:00`) fixed. |
| `Latitude` & `Longitude` | Converted to floats. Out-of-bounds coordinates and invalid `(0.0, 0.0)` tuples mapped to `NaN`. |
| Boolean Indicators (12 Flags) | Messy values (`Yes`, `Y`, `TRUE`, `1`, `No`, `N`, `FALSE`, blanks) normalized into clean boolean `True`/`False`. |
| `Make` & `Color` | Manufacturers (`CHEV` $\rightarrow$ `CHEVROLET`, `TOYT` $\rightarrow$ `TOYOTA`) and colors (`BLK` $\rightarrow$ `BLACK`, `SILV` $\rightarrow$ `SILVER`) standardized via lookup dictionaries. |
| Search Metadata | Missing search outcome fields filled as `"NOT APPLICABLE"`. |
| Feature Engineering | Extracted `Stop_Hour`, `Time_Of_Day` buckets, `Day_Of_Week`, `Month_Name`, `Violation_Category`, and `Accident_Severity_Index`. |

---

## 📊 Key EDA Findings & Insights

- **Total Cleaned Records**: 2,067,788 rows across 1,178,080 distinct traffic stops.
- **Top Violation Category**: *License / Registration / Documentation* (32.4%) followed by *Speeding* (24.1%) and *Vehicle Equipment & Maintenance* (18.6%).
- **Accident Severity**: 56,478 stops (2.73%) involved collisions, resulting in 25,108 personal injuries and 567 fatalities.
- **Peak Enforcement Hours**: Stops peak heavily between **21:00 (9 PM) and 01:00 (1 AM)** and during morning commute hours (**07:00 - 09:00**).
- **Geographic Hotspots**: 3rd District (Silver Spring) and 4th District (Wheaton) account for over 40% of total violation activity.

---

## ⚡ Installation & Execution Guide

### 1. Prerequisites
- Python 3.10+ installed on Windows / macOS / Linux.

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Step 1: Run Data Preprocessing (CSV $\rightarrow$ Parquet)
```bash
python src/preprocessing.py
```

### 4. Step 2: Load SQLite Database & Create Indexes
```bash
python src/database.py
```

### 5. Step 3: Run Automated EDA & Generate Charts
```bash
python eda/generate_eda.py
```

### 6. Step 4: Run Unit Tests
```bash
python -m pytest tests/
```

### 7. Step 5: Launch Interactive Streamlit Dashboard
```bash
streamlit run app.py
```

---

## 🔄 Live Feed Integration (Incremental Ingestion)

The pipeline also stays current by pulling new records from the county's live
open-data API ([Montgomery County Traffic Violations, SODA API](https://data.montgomerycountymd.gov/resource/4mse-ku6q.json)),
which is republished daily.

```
Live API ──► api_client.py ──► schema.py ──► preprocessing.py ──► SQLite
             paging, retries    validate,      same cleaner as     idempotent load
             + backoff          quarantine     the bulk CSV        + watermark
```

| Concern | How it's handled |
| :--- | :--- |
| **Incremental** | Watermark in `data/ingest_state.json`; each run fetches only new days. |
| **Retries** | Timeouts, connection errors, 429 and 5xx are retried with exponential backoff + jitter, honouring `Retry-After`. Other 4xx errors fail fast. |
| **Validation** | Every record is checked with a Pydantic schema (`src/schema.py`). Invalid records go to `data/rejects/<run_id>.jsonl` with the reason. |
| **Fail-closed** | If more than 5% of a run is rejected, nothing is loaded and the run exits non-zero, because the feed has probably changed shape. |
| **Schema drift** | New, unknown fields are logged as warnings. |
| **Idempotent** | Natural keys are stored in `ingest_keys`; re-running a window never duplicates rows. Rows and keys load in one transaction. |
| **Observability** | Logs go to `logs/ingest.log` (rotating). Each run appends counts, duration and status to `data/run_history.jsonl`. |
| **Scheduling** | Airflow DAG `traffic_live_ingest`, daily at 07:30 IST with retries (see below). The Windows Task Scheduler script still works without Docker. |
| **Tests / CI** | `pytest` covers paging, retries, validation, idempotency and failure paths with no network. GitHub Actions runs them on every push. |

### Run it
```bash
python -m src.live_ingest --dry-run      # fetch + validate only
python -m src.live_ingest                # incremental load
python -m src.live_ingest --since 2026-10-01
```
Optional: set `SODA_APP_TOKEN` to raise the county API's rate limit.

### Schedule it (Windows, PowerShell)
```powershell
.\scripts\register_daily_task.ps1 -At "07:30"
```

Problems found and fixed are recorded in [INCIDENTS.md](INCIDENTS.md).

---

## ⚙️ Spark + Airflow

The cleaning step also runs on **PySpark**, orchestrated by **Apache Airflow**, with a
quality gate so bad data never replaces good data.

```
traffic_bulk_etl (on demand)
  check_source ─► spark_transform ─► quality_gate ─► publish ─► load_sqlite
  raw CSV exists   CSV → staging      fail = stop,    swap staging  rebuild DB
                   Parquet            old data kept   into place    + indexes

traffic_live_ingest (daily 07:30 IST)
  live_ingest: county API → validate → load   (3 retries for network errors;
                                               a changed feed fails at once)
```

**Same rules, proven identical.** `src/spark_preprocessing.py` re-implements every rule in
`preprocessing.py` with Spark's built-in column functions (no Python UDFs, which would ship
every row from the JVM to Python and back). `tests/test_spark_parity.py` runs both pipelines
on the same messy CSV and compares every value of every row. The first run found two real
differences (pandas silently treats `N/A` as missing; Spark and NumPy round halves
differently), both fixed: see [INC-002](INCIDENTS.md).

**Quality gate.** Before publishing, `src/quality.py` checks the staged output: required
columns, row count, missing dates, unknown stop hours, missing coordinates, missing vehicle
years and empty IDs. Limits come from profiling the real cleaned data (2,067,788 rows:
0% missing dates, 0% unknown hours, 7.5% missing coordinates, 0.7% missing years). On a
failure the task fails without retrying, and the previous Parquet and database stay in place.

**Benchmark.** `scripts/benchmark_etl.py` times both engines on the same file and checks
the outputs match:

| Input | Machine | pandas | Spark (local) | Outputs identical |
| :--- | :--- | ---: | ---: | :---: |
| 1.2M-row generated sample (388 MB) | 2-CPU Linux VM | 42.4 s | 125.5 s | ✅ 1,173,029 rows |

On one small machine Spark is **slower**: it pays for starting a JVM, two full
de-duplication shuffles and a window over every row, and two cores give it little to
parallelise. pandas also has to hold the whole result in memory to de-duplicate across
chunks, which is where it stops scaling; Spark's version of the same job runs unchanged
on a cluster. For a 2M-row file on a laptop, pandas is the sensible default, and the
Spark job is there for when the data outgrows one machine.

### Run it (Docker Desktop)
```bash
docker compose up --build            # first build takes a few minutes
# open http://localhost:8080 → traffic_bulk_etl → Trigger
docker compose run --rm airflow python -m pytest -q                         # all tests, incl. Spark parity + DAGs
docker compose run --rm airflow python scripts/benchmark_etl.py --csv Traffic_Violations.csv
docker compose down
```
Without the real CSV: `python scripts/make_sample_csv.py --rows 200000 --realistic --out data/sample_raw.csv`
and trigger the DAG with `{"csv_path": "/opt/project/data/sample_raw.csv"}`.

---

## 🤖 Citation or Warning? A Classical-ML Model

`src/citation_model.py`, `scripts/train_citation_model.py`: predicts whether a charge ends in a
**citation** or a **warning**, using logistic regression on the cleaned data (1.97M citation/warning
rows).

**How it is evaluated**
- **Time-based split:** train on 2012–2022 (1,740,977 rows), tune on 2023 (66,876), test on
  2024–2025 (167,260). A random split would leak future enforcement patterns into training.
- **Features:** charge, violation category, district, vehicle type, detection method, day, time
  of day, hour, vehicle age and accident/alcohol/commercial flags. **Race, gender and search
  fields are excluded:** the first two must not drive the prediction, and searches happen after
  the stop starts, so they would leak the outcome.
- Rare categories are folded into `OTHER` using training counts only; the decision threshold
  and regularisation strength are chosen on 2023, never on the test years.

**Results on 2024–2025 (test citation rate 30.7%)**

| Model | ROC-AUC | PR-AUC | F1 | Brier |
|---|---|---|---|---|
| Baseline (always the training citation rate) | 0.500 | 0.307 | 0.000 | 0.238 |
| **Logistic regression** | **0.790** | **0.698** | **0.605** | 0.171 |
| Logistic regression, recalibrated on 2023 | 0.790 | 0.698 | 0.604 | **0.154** |
| Gradient-boosted trees (comparison) | 0.797 | 0.709 | 0.610 | 0.164 |

**What it shows**
- Logistic regression is within 0.007 ROC-AUC of gradient-boosted trees while every weight is
  readable: suspended-licence and DUI charges push hardest towards a citation; equipment and
  registration-paperwork charges push towards a warning.
- **Drift:** citations fell from 57% of citation/warning charges in 2012 to 28% in 2025. The model ranks stops just
  as well on 2024 and 2025 (ROC-AUC 0.790 and 0.789) but its probabilities were too high: it
  predicted 44.6% citations in 2024 when the real rate was 33.4%. Recalibrating on 2023 brought
  that to 34.1% and cut the Brier score from 0.171 to 0.154 without changing the ranking.
- Class weighting changed nothing (training classes are 47/53), so it is reported, not used.

```bash
python scripts/train_citation_model.py --data data/cleaned_traffic_violations.parquet
```
Writes `reports/citation_model.md` and `.json` (about 4 minutes on the full data). Tests:
`tests/test_citation_model.py` (9 tests, synthetic data, no file needed).

---

## 🎯 Actionable Policy Recommendations

1. **Strategic Patrol Scheduling**: Shift active patrol vehicles to high-density arterial corridors during peak night-time hours (21:00 - 01:00) when accident rates spike.
2. **Automated Enforcement**: Install additional automated speed and red-light enforcement cameras in top incident districts (3rd & 4th Districts).
3. **Public Awareness Campaigns**: Launch targeted outreach programs focused on vehicle registration compliance and seatbelt safety.
