# Incident Log

Problems found in the pipeline, what caused them, and how they were fixed.
Newest first. Use the template at the bottom for new entries.

---

## INC-003: Comparing the two outputs ran out of memory at 1.2M rows

| | |
|---|---|
| **Found** | 2026-10-31, first benchmark on a 1.2M-row sample |
| **Severity** | Low: tooling only, no data affected |
| **Status** | Fixed (`src/parity.py`) |
| **Regression test** | `tests/test_spark_parity.py::test_same_rows_and_values` (same code path) |

**What happened.** Both pipelines finished, then the benchmark died silently while comparing
their outputs. The kernel log showed the Python process killed by the out-of-memory killer
at about 4 GB.

**Root cause.** The first comparison turned both whole DataFrames (1.17M rows x 55 columns)
into Python strings at once before hashing them.

**Fix.** Compare one column at a time: normalise a column, hash it, fold it into a running
per-row hash, count its values, then free it. Peak memory for the same comparison dropped
to about 0.7 GB, and the result was the same.

---

## INC-002: Spark output differed from pandas in 2 columns (found by the parity test)

| | |
|---|---|
| **Found** | 2026-10-31, the first run of `tests/test_spark_parity.py` |
| **Severity** | Medium: the Spark job would have written different data than the pandas job |
| **Status** | Fixed (`src/spark_preprocessing.py`) |
| **Regression test** | `tests/test_spark_parity.py::test_same_rows_and_values` |

**What happened.** On a 5,873-row messy sample, 1,085 rows differed between the two outputs.
Per-column value counts pointed at two columns.

**Root cause 1: `Color`.** 570 rows had the raw colour `N/A`. `pandas.read_csv` silently
turns `N/A`, `NA`, `null`, `None` and a dozen similar strings into missing values, so pandas
cleaned them to `UNKNOWN`. Spark reads `N/A` as the text `N/A` and kept it.

**Root cause 2: `Geolocation`.** Pairs like `-77.400745` became `-77.40074` in pandas but
`-77.40075` in Spark. NumPy multiplies by 100,000 and rounds half to even
(-7740074.5 becomes -7740074), while Spark's `round` rounds halves away from zero.

**Fix.** Spark now treats pandas' default missing-value strings as null when it reads the CSV,
and rounds with `rint(x * 1e5) / 1e5`, the same arithmetic NumPy uses. The next run had
0 differing rows, and a 1.17M-row run (which crosses pandas' 500K-row chunk boundaries)
was identical too.

**Lesson.** "It runs and the row counts match" is not "it produces the same data". The
row counts matched here; only a value-level comparison showed the difference.

---

## INC-001: Missing values silently skipped cleaning on pandas 3

| | |
|---|---|
| **Found** | 2026-10-21, while connecting the live county feed |
| **Severity** | Medium: silent data-quality issue, no crash |
| **Status** | Fixed (`src/preprocessing.py`, `_to_text`) |
| **Regression test** | `tests/test_preprocessing.py::test_missing_text_values_filled_on_pandas3` |

**What happened.** The first test that ran feed-shaped records through the existing
cleaner failed: `Search_Type` came out as `NaN` instead of `NOT APPLICABLE`.

**Root cause.** The cleaner did `df[col].astype(str)` and then replaced the strings
`'NAN'`, `'NONE'` and `''` with `UNKNOWN` / `NOT APPLICABLE`. pandas 2 turns missing
values into the text `'nan'`, so that worked. pandas 3.0 keeps them as real missing
values after `astype(str)`, so the replacement never matched. The problem affected
13 text columns (Location, Model, Race, Search_*, ...). Missing values passed straight
through to Parquet/SQLite as NULL, and dashboard filters on `'UNKNOWN'` undercounted.
Nothing errored, so the existing tests (which had no missing values) passed.

**Fix.** Added `_to_text()`, which fills missing values with `''` before converting,
and used it everywhere the cleaner converts text. Works the same on pandas 2 and 3.

**Detection going forward.** The regression test fails on the old code and passes on
the new. CI runs the suite on every push.

**Follow-up.** If the bulk Parquet/DB was built on pandas 3, rebuild it:
`python src/preprocessing.py && python src/database.py`. Check with:
`python -c "import pandas as pd; print(pd.read_parquet('data/cleaned_traffic_violations.parquet')['Model'].isna().sum())"`.
Anything above 0 means the bulk data was affected. Record the count here.

---

## INC-000 (design-time): Live feed schema differs from the bulk CSV

Not an outage. These differences were found before the first live run and handled in
`src/schema.py`:

- Field names differ: `seq_id` vs `SeqID`, `vehicle_type` vs `VehicleType`, and so on.
- The API **omits null fields** from each JSON record, so a page can lack whole
  columns. The cleaner would raise `KeyError`, so every expected column is now filled.
- `geolocation` arrives as an object (`{"latitude": .., "longitude": ..}`), not a
  `"(lat, lon)"` string.
- `date_of_stop` is a floating timestamp (`2026-10-19T00:00:00.000`).
- The cleaner hard-coded `2026` as the latest valid year. From 1 Jan 2027 every live
  record would have lost its date, and 2027 model-year vehicles (already on the road)
  were being nulled. It now uses the current year, plus one for model years.

---

## Template

```
## INC-XXX: <one-line summary>

| | |
|---|---|
| **Detected** | <date/time, and how: failed scheduled run / log alert / run_history> |
| **Severity** | <High/Medium/Low>: <user/data impact> |
| **Status** | <Open / Fixed in commit abc123> |
| **Regression test** | <test name> |

**What happened.** <symptom, with the run_id from data/run_history.jsonl>
**Root cause.** <why>
**Fix.** <what changed>
**Detection going forward.** <test / alert / threshold>
```
