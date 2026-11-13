"""The DAG file loads in Airflow and wires the steps in the right order. Skipped without Airflow."""

import os

import pytest

pytest.importorskip("airflow")
from airflow.models import DagBag  # noqa: E402

DAGS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dags")


@pytest.fixture(scope="module")
def bag():
    return DagBag(dag_folder=DAGS)


def test_dags_import_without_errors(bag):
    assert bag.import_errors == {}
    assert set(bag.dag_ids) == {"traffic_bulk_etl", "traffic_live_ingest"}


def test_bulk_etl_order(bag):
    dag = bag.dags["traffic_bulk_etl"]
    order = ["check_source", "spark_transform", "quality_gate", "publish", "load_sqlite"]
    for upstream, downstream in zip(order, order[1:]):
        assert dag.get_task(downstream).upstream_task_ids == {upstream}
    assert dag.schedule is None or str(dag.timetable.summary) in ("None", "Never, external triggers only")


def test_live_ingest_schedule_and_retries(bag):
    dag = bag.dags["traffic_live_ingest"]
    task = dag.get_task("live_ingest")
    assert task.retries == 3
    assert dag.max_active_runs == 1 and not dag.catchup
