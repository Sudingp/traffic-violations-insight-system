"""
Airflow DAGs for the traffic violations pipeline.

traffic_bulk_etl   (run on demand, e.g. when a new full CSV export arrives)
    check_source -> spark_transform -> quality_gate -> publish -> load_sqlite
    The new data only replaces the old once the quality gate passes, so a bad
    file never reaches the dashboard.

traffic_live_ingest   (daily 07:30 IST; replaces the Windows Task Scheduler job)
    live_ingest: pulls new records from the county API, validates, loads.
    Network errors are retried 3 times; a feed that changed shape fails at once,
    because retrying would not help.

The work itself lives in src/pipeline_tasks.py, so it is unit tested without Airflow.
"""

import os
import sys
from datetime import timedelta

import pendulum
from airflow.sdk.exceptions import AirflowFailException
from airflow.sdk import Param, dag, get_current_context, task

PROJECT_DIR = os.environ.get("TVIS_PROJECT_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from src import pipeline_tasks as steps  # noqa: E402
from src.quality import QualityError  # noqa: E402

DEFAULTS = {"owner": "sudin", "retries": 0}


@dag(
    dag_id="traffic_bulk_etl",
    description="Raw CSV -> Spark cleaning -> quality gate -> Parquet + SQLite",
    schedule=None,
    start_date=pendulum.datetime(2026, 10, 1, tz="Asia/Kolkata"),
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULTS,
    params={"csv_path": Param(steps.RAW_CSV, type="string", description="Raw CSV to clean")},
    tags=["traffic", "spark", "etl"],
)
def traffic_bulk_etl():
    @task
    def check_source(params=None) -> dict:
        return steps.check_source(params["csv_path"])

    @task(execution_timeout=timedelta(hours=1))
    def spark_transform(source: dict) -> str:
        out = steps.staging_path(get_current_context()["run_id"])
        steps.transform(source["path"], out)
        return out

    @task
    def quality_gate(staging: str) -> str:
        try:
            steps.quality_gate(staging)
        except QualityError as exc:
            # Bad data will still be bad on a retry: fail now, keep the old output in place.
            raise AirflowFailException(f"quality gate failed: {exc}") from exc
        return staging

    @task
    def publish(staging: str) -> str:
        return steps.publish(staging)

    @task(execution_timeout=timedelta(hours=1))
    def load_sqlite(final: str) -> dict:
        return steps.load_sqlite(final)

    load_sqlite(publish(quality_gate(spark_transform(check_source()))))


@dag(
    dag_id="traffic_live_ingest",
    description="Daily incremental load from the county's live API",
    schedule="30 7 * * *",
    start_date=pendulum.datetime(2026, 10, 1, tz="Asia/Kolkata"),
    catchup=False,
    max_active_runs=1,
    default_args={"owner": "sudin", "retries": 3, "retry_delay": timedelta(minutes=10),
                  "retry_exponential_backoff": True},
    tags=["traffic", "ingest"],
)
def traffic_live_ingest():
    @task(execution_timeout=timedelta(minutes=30))
    def live_ingest() -> dict:
        try:
            return steps.live_ingest()
        except steps.FeedShapeChanged as exc:
            raise AirflowFailException(str(exc)) from exc

    live_ingest()


traffic_bulk_etl()
traffic_live_ingest()
