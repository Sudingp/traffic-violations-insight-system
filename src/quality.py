"""
Data-quality gate for the cleaned Parquet output.

The Airflow DAG runs this between "transform" and "load": if any check fails,
the task fails and the SQLite database keeps yesterday's good data instead of
being overwritten with a broken file.

Thresholds come from profiling the real cleaned dataset (2,067,788 rows):
0% missing stop dates, 0% unknown stop hours, 7.5% missing coordinates
and 0.7% missing vehicle years. Each limit sits well above today's rate,
so it only trips on a real regression.
"""

import argparse
import json
from typing import Dict, List

import pyarrow.parquet as pq

THRESHOLDS = {
    "min_rows": 1,
    "max_missing_date_pct": 1.0,
    "max_unknown_hour_pct": 1.0,
    "max_missing_coords_pct": 15.0,
    "max_missing_year_pct": 5.0,
}

REQUIRED_COLUMNS = ["SeqID", "Date_Of_Stop", "Datetime_Of_Stop", "Stop_Hour", "Latitude", "Longitude",
                    "Year", "Violation_Category", "Accident_Severity_Index", "Is_Multi_Charge"]


class QualityError(Exception):
    """The cleaned data failed at least one check; nothing should be loaded."""


def _pct(part: int, whole: int) -> float:
    return round(100.0 * part / whole, 3) if whole else 0.0


def profile(parquet_path: str) -> Dict:
    table = pq.read_table(parquet_path, columns=None)
    names = set(table.column_names)
    missing_cols = [c for c in REQUIRED_COLUMNS if c not in names]
    n = table.num_rows
    if missing_cols:
        return {"rows": n, "missing_columns": missing_cols}
    hours = table.column("Stop_Hour").to_pandas()
    seq = table.column("SeqID").to_pandas()
    return {
        "rows": n,
        "missing_columns": [],
        "missing_date_pct": _pct(table.column("Date_Of_Stop").null_count, n),
        "unknown_hour_pct": _pct(int((hours == -1).sum()), n),
        "missing_coords_pct": _pct(table.column("Latitude").null_count, n),
        "missing_year_pct": _pct(table.column("Year").null_count, n),
        "empty_seqid": int((seq.isna() | (seq == "")).sum()),
    }


def failures(stats: Dict, limits: Dict = None) -> List[str]:
    t = dict(THRESHOLDS, **(limits or {}))
    if stats["missing_columns"]:
        return [f"missing columns: {stats['missing_columns']}"]
    problems = []
    if stats["rows"] < t["min_rows"]:
        problems.append(f"only {stats['rows']} rows (need at least {t['min_rows']})")
    for key in ("missing_date", "unknown_hour", "missing_coords", "missing_year"):
        value, limit = stats[f"{key}_pct"], t[f"max_{key}_pct"]
        if value > limit:
            problems.append(f"{key.replace('_', ' ')}: {value}% (limit {limit}%)")
    if stats["empty_seqid"]:
        problems.append(f"{stats['empty_seqid']} rows have no SeqID")
    return problems


def check(parquet_path: str, limits: Dict = None) -> Dict:
    """Profiles the file and raises QualityError listing every failed check."""
    stats = profile(parquet_path)
    problems = failures(stats, limits)
    if problems:
        raise QualityError("; ".join(problems))
    return stats


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Quality gate for the cleaned Parquet file")
    ap.add_argument("parquet")
    a = ap.parse_args()
    print(json.dumps(check(a.parquet), indent=2))
