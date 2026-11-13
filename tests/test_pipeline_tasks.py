"""Tests for the DAG steps (src/pipeline_tasks.py) and the quality gate. No Spark or Airflow needed."""

import os

import numpy as np
import pandas as pd
import pytest

from src import pipeline_tasks as pt
from src import quality


def cleaned_frame(n=100, **overrides):
    df = pd.DataFrame({
        "SeqID": [f"s{i}" for i in range(n)],
        "Date_Of_Stop": pd.to_datetime(["2024-01-01"] * n),
        "Datetime_Of_Stop": pd.to_datetime(["2024-01-01 10:00:00"] * n),
        "Stop_Hour": np.full(n, 10, dtype="int8"),
        "Latitude": np.full(n, 39.1), "Longitude": np.full(n, -77.1),
        "Year": np.full(n, 2015.0), "Violation_Category": ["Speeding"] * n,
        "Accident_Severity_Index": np.zeros(n, dtype=int), "Is_Multi_Charge": [False] * n,
    })
    for col, values in overrides.items():
        df[col] = values
    return df


def write(df, tmp_path, name="clean.parquet"):
    path = str(tmp_path / name)
    df.to_parquet(path, index=False)
    return path


def test_quality_gate_passes_on_clean_data(tmp_path):
    stats = pt.quality_gate(write(cleaned_frame(), tmp_path))
    assert stats["rows"] == 100 and stats["missing_coords_pct"] == 0.0


def test_quality_gate_lists_every_failure(tmp_path):
    lat = [np.nan] * 30 + [39.1] * 70
    hours = np.array([-1] * 5 + [10] * 95, dtype="int8")
    seq = [""] + [f"s{i}" for i in range(99)]
    path = write(cleaned_frame(Latitude=lat, Stop_Hour=hours, SeqID=seq), tmp_path)
    with pytest.raises(quality.QualityError) as err:
        pt.quality_gate(path)
    msg = str(err.value)
    assert "missing coords: 30.0%" in msg and "unknown hour: 5.0%" in msg and "1 rows have no SeqID" in msg


def test_quality_gate_rejects_missing_columns_and_empty_files(tmp_path):
    with pytest.raises(quality.QualityError, match="missing columns"):
        pt.quality_gate(write(cleaned_frame().drop(columns=["Year"]), tmp_path))
    with pytest.raises(quality.QualityError, match="only 0 rows"):
        pt.quality_gate(write(cleaned_frame(0), tmp_path, "empty.parquet"))


def test_check_source(tmp_path):
    with pytest.raises(FileNotFoundError):
        pt.check_source(str(tmp_path / "missing.csv"))
    (tmp_path / "raw.csv").write_text("a,b\n1,2\n")
    assert pt.check_source(str(tmp_path / "raw.csv"))["path"].endswith("raw.csv")


def test_publish_swaps_in_new_output_and_keeps_old_on_failure(tmp_path, monkeypatch):
    final, staging = tmp_path / "final.parquet", tmp_path / "staging.parquet"
    final.mkdir(); (final / "part-0").write_text("old")
    staging.mkdir(); (staging / "part-0").write_text("new")
    pt.publish(str(staging), str(final))
    assert (final / "part-0").read_text() == "new" and not staging.exists()
    assert not (tmp_path / "final.parquet.previous").exists()

    # A failed swap must leave the previous good output in place
    staging.mkdir(); (staging / "part-0").write_text("newer")
    real_replace = os.replace

    def flaky(src, dst):
        if str(src) == str(staging):
            raise OSError("disk full")
        return real_replace(src, dst)

    monkeypatch.setattr(pt.os, "replace", flaky)
    with pytest.raises(OSError):
        pt.publish(str(staging), str(final))
    assert (final / "part-0").read_text() == "new"


def test_staging_path_is_safe_for_run_ids():
    path = pt.staging_path("manual__2026-10-31T14:00:00+00:00")
    assert ":" not in os.path.basename(path) and "+" not in os.path.basename(path)


def test_live_ingest_maps_failures(monkeypatch):
    import src.live_ingest as li
    monkeypatch.setattr(li, "run", lambda *a, **k: {"status": "success", "run_id": "r1", "inserted": 5})
    assert pt.live_ingest("x.db")["inserted"] == 5

    monkeypatch.setattr(li, "run", lambda *a, **k: {"status": "failed", "error": "Reject rate 9.0% exceeds limit 5.0%"})
    with pytest.raises(pt.FeedShapeChanged):
        pt.live_ingest("x.db")

    monkeypatch.setattr(li, "run", lambda *a, **k: {"status": "failed", "error": "HTTP 503 after 5 retries"})
    with pytest.raises(RuntimeError, match="503"):
        pt.live_ingest("x.db")


def test_load_sqlite_from_parquet(tmp_path):
    df = cleaned_frame(10)
    for col in ["Accident", "Personal_Injury", "Fatal", "Alcohol", "Search_Conducted"]:
        df[col] = False
    for col in ["Agency", "SubAgency", "Violation_Type", "Make", "Gender", "Race"]:
        df[col] = "X"
    kpis = pt.load_sqlite(write(df, tmp_path), str(tmp_path / "db" / "t.db"))
    assert kpis["total_records"] == 10 and kpis["total_stops"] == 10
