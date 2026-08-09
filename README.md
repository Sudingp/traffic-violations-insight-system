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
│   └── database.py                       # SQLite database manager & indexing engine
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

## 🎯 Actionable Policy Recommendations

1. **Strategic Patrol Scheduling**: Shift active patrol vehicles to high-density arterial corridors during peak night-time hours (21:00 - 01:00) when accident rates spike.
2. **Automated Enforcement**: Install additional automated speed and red-light enforcement cameras in top incident districts (3rd & 4th Districts).
3. **Public Awareness Campaigns**: Launch targeted outreach programs focused on vehicle registration compliance and seatbelt safety.
