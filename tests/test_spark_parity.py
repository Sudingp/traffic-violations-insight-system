"""
The Spark pipeline must produce the same data as the pandas pipeline.

Runs both on the same messy CSV (scripts/make_sample_csv.py) and compares every
row and column. Skipped when PySpark or Java is not installed.
"""

import os
import shutil
import sys

import pandas as pd
import pytest

pyspark = pytest.importorskip("pyspark")
if shutil.which("java") is None and not os.environ.get("JAVA_HOME"):
    pytest.skip("Java is not installed", allow_module_level=True)

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts"))
from make_sample_csv import write_csv  # noqa: E402

from src.parity import compare  # noqa: E402
from src.preprocessing import execute_etl_pipeline  # noqa: E402
from src.spark_preprocessing import clean, make_spark, run  # noqa: E402


@pytest.fixture(scope="module")
def spark():
    s = make_spark("parity-tests", driver_memory="1g")
    yield s
    s.stop()


@pytest.fixture(scope="module")
def sample_csv(tmp_path_factory):
    return write_csv(str(tmp_path_factory.mktemp("raw") / "raw.csv"), 6000)


@pytest.fixture(scope="module")
def both(spark, sample_csv, tmp_path_factory):
    out = tmp_path_factory.mktemp("out")
    p = execute_etl_pipeline(sample_csv, str(out / "pandas.parquet"))
    run(sample_csv, str(out / "spark.parquet"), spark=spark)
    s = pd.read_parquet(out / "spark.parquet")
    return pd.read_parquet(out / "pandas.parquet"), s, p


def test_same_rows_and_values(both):
    pandas_df, spark_df, _ = both
    report = compare(pandas_df, spark_df)
    assert report["column_differences"] == {}, report["column_differences"]
    assert report["identical"], report


def test_same_column_order(both):
    pandas_df, spark_df, _ = both
    assert list(spark_df.columns) == list(pandas_df.columns)


def test_dates_load_into_sqlite_like_pandas_output(both, tmp_path):
    """database.py calls .dt.strftime on the date columns; Spark's Parquet must allow that."""
    _, spark_df, _ = both
    assert pd.api.types.is_datetime64_any_dtype(spark_df["Date_Of_Stop"])
    assert pd.api.types.is_datetime64_any_dtype(spark_df["Datetime_Of_Stop"])
    assert getattr(spark_df["Datetime_Of_Stop"].dt, "tz", None) is None


def test_dirty_values_are_cleaned(spark):
    raw = spark.createDataFrame(pd.DataFrame({
        'SeqID': [' a ', 'a', 'b'], 'Date Of Stop': ['05/01/2023', '05/01/2023', '06/15/2031'],
        'Time Of Stop': ['23.11.00', '8:5', 'abc'], 'Latitude': ['0', '39.1', '91'],
        'Longitude': ['0', '-77.2', '-77'], 'Make': ['TOYT', 'VW', ''], 'Gender': ['male', 'F', 'x'],
        'Violation Type': ['ESERO', '', 'warning'], 'Fatal': ['No', 'Y', 'TRUE'],
        'Personal Injury': ['Yes', 'No', ''], 'Property Damage': ['', '', '1'],
    }).reindex(columns=[c for c in __import__('make_sample_csv').COLUMNS], fill_value=''))
    rows = {r['Time_Of_Stop']: r for r in clean(raw).collect()}
    a, b, c = rows['23:11:00'], rows['08:05:00'], rows['00:00:00']
    assert a['SeqID'] == 'a' and a['Is_Multi_Charge'] and b['Is_Multi_Charge'] and not c['Is_Multi_Charge']
    assert a['Latitude'] is None and b['Latitude'] == 39.1 and c['Latitude'] is None
    assert b['Geolocation'] == '(39.1, -77.2)' and a['Geolocation'] == 'N/A'
    assert (a['Make'], b['Make'], c['Make']) == ('TOYOTA', 'VOLKSWAGEN', 'UNKNOWN')
    assert (a['Gender'], b['Gender'], c['Gender']) == ('M', 'F', 'Unknown')
    assert (a['Violation_Type'], b['Violation_Type'], c['Violation_Type']) == ('Esero', 'Citation', 'Warning')
    assert (a['Accident_Severity_Index'], b['Accident_Severity_Index'], c['Accident_Severity_Index']) == (2, 3, 3)
    assert c['Date_Of_Stop'] is None and c['Stop_Year'] == 1970     # future date dropped, like pandas
    assert a['Stop_Hour'] == 23 and a['Time_Of_Day'] == 'Evening (18:00-24:00)'
