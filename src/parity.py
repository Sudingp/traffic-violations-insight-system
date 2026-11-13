"""
Checks that the pandas and Spark pipelines produced the same data.

Row order differs between engines, so rows are compared as a multiset: each
column is normalised (same types, rounded floats, missing = one marker) and
hashed, the column hashes are combined into one hash per row, and the two row
hash counts are compared. Per-column value counts then show *where* any
difference is, which is what you need to debug it.

Works one column at a time, so comparing two 2M-row files fits in a laptop's
memory (the first version turned whole frames into strings and ran out of
memory at 1.2M rows).
"""

from typing import Dict, Union

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

Source = Union[str, pd.DataFrame]


def _columns(src: Source):
    if isinstance(src, pd.DataFrame):
        return list(src.columns), len(src)
    ds = pq.ParquetDataset(src)                      # a single file or Spark's folder of parts
    names = [n for n in ds.schema.names if not n.startswith("__")]
    return names, ds.read(columns=[names[0]]).num_rows


def _load(src: Source, col: str) -> pd.Series:
    if isinstance(src, pd.DataFrame):
        return src[col].reset_index(drop=True)
    return pq.ParquetDataset(src).read(columns=[col]).column(col).to_pandas()


def normalise(s: pd.Series) -> pd.Series:
    """One canonical text form per value, '<null>' for missing."""
    if isinstance(s.dtype, pd.CategoricalDtype):
        s = s.astype(object)
    if pd.api.types.is_datetime64_any_dtype(s):
        s = s.dt.strftime('%Y-%m-%d %H:%M:%S')
    elif pd.api.types.is_float_dtype(s):
        s = s.round(6)
    elif pd.api.types.is_integer_dtype(s) and not pd.api.types.is_bool_dtype(s):
        s = s.astype('int64')
    s = s.astype(object)
    return s.where(s.notna(), '<null>').astype(str)


def compare(pandas_src: Source, spark_src: Source) -> Dict:
    """Returns row counts, rows only in one output, and per-column differences."""
    ca, na = _columns(pandas_src)
    cb, nb = _columns(spark_src)
    report = {
        "rows_pandas": na, "rows_spark": nb,
        "columns_only_in_pandas": sorted(set(ca) - set(cb)),
        "columns_only_in_spark": sorted(set(cb) - set(ca)),
    }
    cols = [c for c in ca if c in cb]
    row_a, row_b = np.zeros(na, dtype=np.uint64), np.zeros(nb, dtype=np.uint64)
    col_diffs = {}
    for i, c in enumerate(cols):
        a, b = normalise(_load(pandas_src, c)), normalise(_load(spark_src, c))
        mult = np.uint64(1_000_003 + 2 * i)          # different weight per column position
        with np.errstate(over='ignore'):
            row_a = row_a * mult + pd.util.hash_array(a.to_numpy())
            row_b = row_b * mult + pd.util.hash_array(b.to_numpy())
        d = a.value_counts().sub(b.value_counts(), fill_value=0)
        d = d[d != 0]
        if len(d):
            col_diffs[c] = {k: int(v) for k, v in d.abs().sort_values(ascending=False).head(5).items()}
        del a, b
    diff = pd.Series(row_a).value_counts().sub(pd.Series(row_b).value_counts(), fill_value=0)
    report["rows_only_in_pandas"] = int(diff[diff > 0].sum())
    report["rows_only_in_spark"] = int(-diff[diff < 0].sum())
    report["column_differences"] = col_diffs
    report["identical"] = (report["rows_only_in_pandas"] == 0 and report["rows_only_in_spark"] == 0
                           and not report["columns_only_in_pandas"] and not report["columns_only_in_spark"])
    return report
