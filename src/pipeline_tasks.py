"""
The steps the Airflow DAGs run, as plain functions.

Keeping the logic here (not inside the DAG file) means every step can be unit
tested and run by hand without Airflow; the DAG file only wires them together.

Bulk ETL:  check_source -> transform (Spark) -> quality_gate -> publish -> load_sqlite
Live feed: live_ingest (daily, replaces the Windows Task Scheduler job)
"""

import logging
import os
import shutil
from typing import Dict, Optional

from src import quality

logger = logging.getLogger("tvis.pipeline")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.environ.get("TVIS_DATA_DIR", os.path.join(PROJECT_ROOT, "data"))
RAW_CSV = os.environ.get("TVIS_RAW_CSV", os.path.join(PROJECT_ROOT, "Traffic_Violations.csv"))
CLEANED = os.path.join(DATA_DIR, "cleaned_traffic_violations_spark.parquet")
DB_PATH = os.path.join(DATA_DIR, "traffic_violations.db")


class FeedShapeChanged(Exception):
    """The live feed rejected too many records; retrying will not fix it."""


def check_source(csv_path: str = RAW_CSV) -> Dict:
    if not os.path.isfile(csv_path):
        raise FileNotFoundError(f"raw CSV not found: {csv_path}")
    size = os.path.getsize(csv_path)
    size_mb = round(size / 1024 ** 2, 1)
    if size == 0:
        raise ValueError(f"raw CSV is empty: {csv_path}")
    logger.info("Source %s (%.1f MB)", csv_path, size_mb)
    return {"path": csv_path, "size_mb": size_mb}


def staging_path(run_id: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in run_id)
    return os.path.join(DATA_DIR, "staging", f"cleaned_{safe}.parquet")


def transform(csv_path: str, out_path: str) -> Dict:
    # Imported here so the rest of this module works without Spark installed.
    from src.spark_preprocessing import run
    result = run(csv_path, out_path)
    logger.info("Spark transform: %s rows in %ss -> %s", result["rows_out"], result["seconds"], out_path)
    return result


def quality_gate(parquet_path: str, limits: Optional[Dict] = None) -> Dict:
    stats = quality.check(parquet_path, limits)   # raises QualityError on failure
    logger.info("Quality gate passed: %s", stats)
    return stats


def publish(staging: str, final: str = CLEANED) -> str:
    """Swaps the checked staging output into place; the old copy is kept until the swap succeeds."""
    previous = final + ".previous"
    if os.path.exists(previous):
        shutil.rmtree(previous) if os.path.isdir(previous) else os.remove(previous)
    if os.path.exists(final):
        os.replace(final, previous)
    try:
        os.replace(staging, final)
    except OSError:
        if os.path.exists(previous):
            os.replace(previous, final)   # put the old data back
        raise
    if os.path.exists(previous):
        shutil.rmtree(previous) if os.path.isdir(previous) else os.remove(previous)
    return final


def load_sqlite(parquet_path: str = CLEANED, db_path: str = DB_PATH) -> Dict:
    from src.database import TrafficViolationsDB
    db = TrafficViolationsDB(db_path)
    db.load_data_from_parquet(parquet_path)
    kpis = db.get_summary_kpis()
    logger.info("Loaded SQLite: %s", kpis)
    return {k: (float(v) if isinstance(v, float) else int(v)) for k, v in kpis.items()}


def live_ingest(db_path: str = DB_PATH, dry_run: bool = False) -> Dict:
    """One incremental run of the county feed. Raises if the run failed, so Airflow marks it red."""
    from src.live_ingest import run
    summary = run(db_path, data_dir=DATA_DIR, dry_run=dry_run)
    if summary["status"] in ("success", "dry_run"):
        return {k: summary.get(k) for k in ("run_id", "status", "fetched", "valid", "rejected",
                                            "inserted", "watermark", "duration_s")}
    error = summary.get("error", "unknown error")
    if error.startswith("Reject rate"):
        raise FeedShapeChanged(error)
    raise RuntimeError(f"live ingest failed: {error}")
