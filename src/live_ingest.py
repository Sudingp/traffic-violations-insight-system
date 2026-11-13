"""
Incremental ingestion job: live county feed -> validated -> cleaned -> SQLite.

Run it:
    python -m src.live_ingest                 # normal scheduled run
    python -m src.live_ingest --dry-run       # fetch + validate, write nothing
    python -m src.live_ingest --since 2026-10-01

What one run does
-----------------
1. Reads the watermark (last date_of_stop already loaded) from data/ingest_state.json.
   First run: starts after the newest date already in the DB (from the bulk CSV),
   or 7 days back if there is no DB yet.
2. Pages through the feed from the watermark, with retries (api_client.py).
3. Validates every record (schema.py). Bad records go to data/rejects/<run_id>.jsonl.
   If the reject rate exceeds --max-reject-rate the run fails *before loading anything*:
   a sudden spike in rejects almost always means the feed changed shape.
4. Cleans valid records with the same preprocessing.py used for the bulk CSV.
5. Loads idempotently: each row's natural key is recorded in `ingest_keys`, so
   re-running the same window never duplicates rows. Load is one transaction.
6. Advances the watermark only after a successful load, and appends a summary line
   to data/run_history.jsonl (counts, duration, status) for monitoring.
"""

import argparse
import json
import logging
import os
import sqlite3
import sys
import time
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import pandas as pd

from src.api_client import FeedError, TrafficViolationsClient
from src.logging_setup import setup_logging
from src.preprocessing import process_traffic_violations_df
from src.schema import record_key, to_csv_columns, validate_records

logger = logging.getLogger("tvis.ingest")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
TABLE = "traffic_violations"


class IngestAborted(Exception):
    """Run stopped deliberately (e.g. reject rate too high); nothing was loaded."""


# ---------------------------------------------------------------------- #
# State (watermark)
# ---------------------------------------------------------------------- #
def load_state(state_path: str) -> dict:
    if os.path.exists(state_path):
        with open(state_path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state(state_path: str, state: dict) -> None:
    # Write to a temp file then rename, so a crash mid-write can't corrupt the watermark.
    tmp = state_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, state_path)


def max_date_in_db(conn: sqlite3.Connection) -> Optional[str]:
    try:
        row = conn.execute(f"SELECT MAX(Date_Of_Stop) FROM {TABLE}").fetchone()
    except sqlite3.OperationalError:  # table doesn't exist yet
        return None
    return row[0] if row and row[0] else None


def resolve_start(state: dict, conn: sqlite3.Connection, since: Optional[str]):
    """Return (start_date, inclusive)."""
    if since:
        return since, True
    if state.get("watermark"):
        # Inclusive: the county can publish more records for the watermark day later.
        return state["watermark"], True
    db_max = max_date_in_db(conn)
    if db_max:
        # First live run on top of the bulk CSV: start strictly after its last day,
        # because bulk rows have no keys in ingest_keys and would otherwise duplicate.
        return db_max[:10], False
    return (date.today() - timedelta(days=7)).isoformat(), True


# ---------------------------------------------------------------------- #
# Load
# ---------------------------------------------------------------------- #
def ensure_key_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS ingest_keys ("
        " record_key TEXT PRIMARY KEY, run_id TEXT NOT NULL, loaded_at TEXT NOT NULL)"
    )


def prepare_for_sqlite(df: pd.DataFrame) -> pd.DataFrame:
    """Same type conversions database.py applies to the bulk load."""
    df = df.copy()
    for col in df.select_dtypes(include=["category"]).columns:
        df[col] = df[col].astype(str)
    if "Date_Of_Stop" in df.columns:
        df["Date_Of_Stop"] = pd.to_datetime(df["Date_Of_Stop"]).dt.strftime("%Y-%m-%d")
    if "Datetime_Of_Stop" in df.columns:
        df["Datetime_Of_Stop"] = pd.to_datetime(df["Datetime_Of_Stop"]).dt.strftime("%Y-%m-%d %H:%M:%S")
    return df


def load_new_rows(conn: sqlite3.Connection, valid: list, run_id: str) -> dict:
    """Clean and insert records not loaded before. Returns counts."""
    ensure_key_table(conn)

    # Dedupe within the batch and against everything already loaded.
    keyed = {}
    for rec in valid:
        keyed.setdefault(record_key(rec), rec)
    keys = list(keyed)
    already = set()
    for i in range(0, len(keys), 500):  # stay under SQLite's variable limit
        chunk = keys[i:i + 500]
        q = f"SELECT record_key FROM ingest_keys WHERE record_key IN ({','.join('?' * len(chunk))})"
        already |= {r[0] for r in conn.execute(q, chunk)}
    new_keys = [k for k in keys if k not in already]
    skipped = len(valid) - len(new_keys)

    if not new_keys:
        return {"inserted": 0, "skipped_duplicates": skipped}

    raw_df = pd.DataFrame(to_csv_columns([keyed[k] for k in new_keys]))
    clean = prepare_for_sqlite(process_traffic_violations_df(raw_df))

    now = datetime.now(timezone.utc).isoformat()
    with conn:  # one transaction: rows and keys land together or not at all
        clean.to_sql(TABLE, conn, if_exists="append", index=False)
        conn.executemany(
            "INSERT INTO ingest_keys (record_key, run_id, loaded_at) VALUES (?, ?, ?)",
            [(k, run_id, now) for k in new_keys],
        )
    return {"inserted": len(clean), "skipped_duplicates": skipped}


# ---------------------------------------------------------------------- #
# Orchestration
# ---------------------------------------------------------------------- #
def run(
    db_path: str,
    data_dir: str = DATA_DIR,
    since: Optional[str] = None,
    dry_run: bool = False,
    max_reject_rate: float = 0.05,
    client: Optional[TrafficViolationsClient] = None,
) -> dict:
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6]
    started = time.monotonic()
    os.makedirs(data_dir, exist_ok=True)
    state_path = os.path.join(data_dir, "ingest_state.json")
    summary = {"run_id": run_id, "started_at": datetime.now(timezone.utc).isoformat(),
               "dry_run": dry_run, "status": "running"}
    client = client or TrafficViolationsClient()
    conn = sqlite3.connect(db_path)

    try:
        state = load_state(state_path)
        start, inclusive = resolve_start(state, conn, since)
        summary["window_start"] = start
        summary["window_inclusive"] = inclusive
        logger.info("[%s] Ingesting from %s (%s)", run_id, start, "inclusive" if inclusive else "exclusive")

        records = []
        for page in client.fetch_since(start, inclusive=inclusive):
            records.extend(page)
        summary["fetched"] = len(records)

        valid, rejected, unknown = validate_records(records)
        summary.update(valid=len(valid), rejected=len(rejected), unknown_fields=sorted(unknown))

        if rejected:
            rej_dir = os.path.join(data_dir, "rejects")
            os.makedirs(rej_dir, exist_ok=True)
            rej_path = os.path.join(rej_dir, f"{run_id}.jsonl")
            with open(rej_path, "w", encoding="utf-8") as f:
                for r in rejected:
                    f.write(json.dumps(r, default=str) + "\n")
            logger.warning("[%s] Quarantined %d invalid records -> %s", run_id, len(rejected), rej_path)

        reject_rate = len(rejected) / len(records) if records else 0.0
        summary["reject_rate"] = round(reject_rate, 4)
        if reject_rate > max_reject_rate:
            raise IngestAborted(
                f"Reject rate {reject_rate:.1%} exceeds limit {max_reject_rate:.1%}; "
                "feed may have changed shape. Nothing was loaded."
            )

        if dry_run:
            summary.update(inserted=0, skipped_duplicates=0, status="dry_run")
        else:
            summary.update(load_new_rows(conn, valid, run_id))
            if valid:
                newest = max(str(r["date_of_stop"])[:10] for r in valid)
                state["watermark"] = max(newest, state.get("watermark", ""))
            state["last_success_run_id"] = run_id
            save_state(state_path, state)
            summary["status"] = "success"
        summary["watermark"] = state.get("watermark")

    except (FeedError, IngestAborted) as exc:
        summary.update(status="failed", error=str(exc))
        logger.error("[%s] Run failed: %s", run_id, exc)
    except Exception as exc:  # unexpected: log with traceback, still record the run
        summary.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        logger.exception("[%s] Unexpected error", run_id)
    finally:
        conn.close()
        summary["duration_s"] = round(time.monotonic() - started, 2)
        with open(os.path.join(data_dir, "run_history.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(summary, default=str) + "\n")
        logger.info(
            "[%s] %s | fetched=%s valid=%s rejected=%s inserted=%s dupes_skipped=%s | %.1fs",
            run_id, summary["status"], summary.get("fetched"), summary.get("valid"),
            summary.get("rejected"), summary.get("inserted"),
            summary.get("skipped_duplicates"), summary["duration_s"],
        )
    return summary


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Incremental ingest from the live county feed.")
    parser.add_argument("--db", default=os.path.join(DATA_DIR, "traffic_violations.db"))
    parser.add_argument("--since", help="Override start date (YYYY-MM-DD), inclusive")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and validate only")
    parser.add_argument("--max-reject-rate", type=float, default=0.05)
    args = parser.parse_args(argv)

    setup_logging(os.path.join(PROJECT_ROOT, "logs"))
    summary = run(args.db, since=args.since, dry_run=args.dry_run,
                  max_reject_rate=args.max_reject_rate)
    # Non-zero exit code lets Task Scheduler / CI mark the run as failed.
    return 0 if summary["status"] in ("success", "dry_run") else 1


if __name__ == "__main__":
    sys.exit(main())
