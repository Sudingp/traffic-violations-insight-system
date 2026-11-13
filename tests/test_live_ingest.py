"""End-to-end tests for the incremental ingestion job (no network)."""

import json
import os
import sqlite3

import pytest

from src import live_ingest
from src.api_client import TrafficViolationsClient


def run_job(tmp_path, session, **kw):
    client = TrafficViolationsClient(session=session, sleep=lambda s: None, page_size=100)
    return live_ingest.run(str(tmp_path / "tv.db"), data_dir=str(tmp_path), client=client, **kw)


def count_rows(tmp_path):
    with sqlite3.connect(tmp_path / "tv.db") as c:
        return c.execute("SELECT COUNT(*) FROM traffic_violations").fetchone()[0]


def history(tmp_path):
    with open(tmp_path / "run_history.jsonl") as f:
        return [json.loads(line) for line in f]


def test_first_run_loads_and_sets_watermark(tmp_path, fake_session, ok, record_factory):
    recs = [record_factory(seq_id="s1"), record_factory(seq_id="s2", date_of_stop="2026-10-20T00:00:00.000")]
    summary = run_job(tmp_path, fake_session([ok(recs)]))

    assert summary["status"] == "success"
    assert summary["inserted"] == 2
    assert count_rows(tmp_path) == 2
    state = json.loads((tmp_path / "ingest_state.json").read_text())
    assert state["watermark"] == "2026-10-20"


def test_rerun_same_window_is_idempotent(tmp_path, fake_session, ok, record_factory):
    recs = [record_factory(seq_id="s1"), record_factory(seq_id="s2")]
    run_job(tmp_path, fake_session([ok(recs)]))
    summary = run_job(tmp_path, fake_session([ok(recs + [record_factory(seq_id="s3")])]))

    assert summary["inserted"] == 1
    assert summary["skipped_duplicates"] == 2
    assert count_rows(tmp_path) == 3


def test_second_run_uses_watermark_inclusive(tmp_path, fake_session, ok, record_factory):
    run_job(tmp_path, fake_session([ok([record_factory()])]))
    session = fake_session([ok([])])
    run_job(tmp_path, session)
    assert session.calls[0]["$where"] == "date_of_stop >= '2026-10-19T00:00:00'"


def test_first_run_on_top_of_bulk_db_starts_after_last_day(tmp_path, fake_session, ok):
    with sqlite3.connect(tmp_path / "tv.db") as c:
        c.execute("CREATE TABLE traffic_violations (Date_Of_Stop TEXT)")
        c.execute("INSERT INTO traffic_violations VALUES ('2026-08-05')")
    session = fake_session([ok([])])
    run_job(tmp_path, session)
    assert session.calls[0]["$where"] == "date_of_stop > '2026-08-05T00:00:00'"


def test_bad_records_quarantined_good_ones_loaded(tmp_path, fake_session, ok, record_factory):
    recs = [record_factory(seq_id=f"s{i}") for i in range(30)] + [record_factory(seq_id="")]
    summary = run_job(tmp_path, fake_session([ok(recs)]))

    assert summary["status"] == "success"
    assert summary["inserted"] == 30 and summary["rejected"] == 1
    rejects = list((tmp_path / "rejects").glob("*.jsonl"))
    assert len(rejects) == 1
    assert json.loads(rejects[0].read_text().splitlines()[0])["record"]["seq_id"] == ""


def test_reject_spike_aborts_without_loading(tmp_path, fake_session, ok, record_factory):
    recs = [record_factory(seq_id="ok")] + [record_factory(description="") for _ in range(3)]
    summary = run_job(tmp_path, fake_session([ok(recs)]))

    assert summary["status"] == "failed"
    assert "Reject rate" in summary["error"]
    assert not (tmp_path / "ingest_state.json").exists()  # watermark not advanced
    with sqlite3.connect(tmp_path / "tv.db") as c:
        tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master")}
    assert "traffic_violations" not in tables


def test_feed_outage_fails_cleanly_and_is_recorded(tmp_path, fake_session, http_error):
    summary = run_job(tmp_path, fake_session([http_error(503)] * 5))
    assert summary["status"] == "failed"
    assert "after 5 attempts" in summary["error"]
    assert history(tmp_path)[-1]["status"] == "failed"


def test_dry_run_writes_nothing(tmp_path, fake_session, ok, record_factory):
    summary = run_job(tmp_path, fake_session([ok([record_factory()])]), dry_run=True)
    assert summary["status"] == "dry_run"
    assert not (tmp_path / "ingest_state.json").exists()


def test_cli_exit_code_reflects_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(live_ingest, "run", lambda *a, **k: {"status": "failed"})
    monkeypatch.setattr(live_ingest, "setup_logging", lambda *a, **k: None)
    assert live_ingest.main(["--db", str(tmp_path / "x.db")]) == 1
