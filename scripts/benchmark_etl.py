"""
Runs the pandas and Spark pipelines on the same CSV, times both, and checks that
the outputs are identical (src/parity.py). Writes the result to docs/benchmark.json.

    python scripts/benchmark_etl.py --csv Traffic_Violations.csv
    python scripts/benchmark_etl.py --sample-rows 500000        # no real file needed
"""

import argparse
import contextlib
import io
import json
import os
import platform
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from src.parity import compare  # noqa: E402
from src.preprocessing import execute_etl_pipeline  # noqa: E402
from src.spark_preprocessing import make_spark, run as spark_run  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", help="raw CSV (default: generate a sample)")
    ap.add_argument("--sample-rows", type=int, default=500_000)
    ap.add_argument("--out-dir", default=os.path.join(ROOT, "data", "benchmark"))
    ap.add_argument("--report", default=os.path.join(ROOT, "docs", "benchmark.json"))
    a = ap.parse_args()

    os.makedirs(a.out_dir, exist_ok=True)
    csv = a.csv
    if not csv:
        from make_sample_csv import write_csv
        csv = write_csv(os.path.join(a.out_dir, "sample_raw.csv"), a.sample_rows)
    size_mb = round(os.path.getsize(csv) / 1024 ** 2, 1)
    print(f"Input: {csv} ({size_mb} MB)")

    print("pandas: running...")
    t = time.time()
    with contextlib.redirect_stdout(io.StringIO()):
        execute_etl_pipeline(csv, os.path.join(a.out_dir, "pandas.parquet"))
    pandas_s = round(time.time() - t, 1)
    print(f"pandas: {pandas_s}s")

    spark = make_spark("benchmark")
    spark.sparkContext.setLogLevel("ERROR")
    print("spark: running...")
    result = spark_run(csv, os.path.join(a.out_dir, "spark.parquet"), spark=spark)
    cores = spark.sparkContext.defaultParallelism
    spark.stop()
    print(f"spark: {result['seconds']}s on {cores} cores")

    print("Comparing outputs...")
    report = compare(os.path.join(a.out_dir, "pandas.parquet"), os.path.join(a.out_dir, "spark.parquet"))
    summary = {
        "input": os.path.basename(csv), "input_mb": size_mb,
        "pandas_seconds": pandas_s, "spark_seconds": result["seconds"], "spark_cores": cores,
        "machine": f"{platform.system()} {platform.machine()}, {os.cpu_count()} CPUs",
        "parity": report,
    }
    os.makedirs(os.path.dirname(a.report), exist_ok=True)
    with open(a.report, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps({k: v for k, v in summary.items() if k != "parity"}, indent=2))
    print("Identical outputs:", report["identical"],
          "| rows pandas/spark:", report["rows_pandas"], report["rows_spark"])
    if report["column_differences"]:
        print("Columns that differ:", json.dumps(report["column_differences"], indent=2))
    print(f"Saved {a.report}")


if __name__ == "__main__":
    main()
