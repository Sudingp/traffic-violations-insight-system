"""Tests for feed schema validation and field mapping."""

from datetime import date, timedelta

import pandas as pd

from src.preprocessing import process_traffic_violations_df
from src.schema import record_key, to_csv_columns, validate_records


def test_valid_record_passes(record_factory):
    valid, rejected, unknown = validate_records([record_factory()])
    assert len(valid) == 1 and rejected == [] and unknown == set()


def test_missing_seq_id_rejected(record_factory):
    rec = record_factory()
    del rec["seq_id"]
    valid, rejected, _ = validate_records([rec])
    assert valid == []
    assert any(e.startswith("seq_id") for e in rejected[0]["errors"])


def test_blank_description_rejected(record_factory):
    _, rejected, _ = validate_records([record_factory(description="   ")])
    assert "description" in rejected[0]["errors"][0]


def test_future_date_rejected(record_factory):
    future = (date.today() + timedelta(days=3)).isoformat() + "T00:00:00.000"
    _, rejected, _ = validate_records([record_factory(date_of_stop=future)])
    assert "future" in rejected[0]["errors"][0]


def test_garbage_date_and_coordinates_rejected(record_factory):
    _, rejected, _ = validate_records([
        record_factory(date_of_stop="not-a-date"),
        record_factory(latitude="north-ish"),
    ])
    assert len(rejected) == 2


def test_rejected_record_keeps_original_payload(record_factory):
    rec = record_factory(seq_id="")
    _, rejected, _ = validate_records([rec])
    assert rejected[0]["record"] == rec


def test_unknown_field_flags_schema_drift_but_still_loads(record_factory):
    valid, _, unknown = validate_records([record_factory(officer_badge="123")])
    assert len(valid) == 1
    assert unknown == {"officer_badge"}


def test_socrata_computed_columns_not_flagged_as_drift(record_factory):
    _, _, unknown = validate_records([record_factory()])
    assert unknown == set()


def test_record_key_distinguishes_charges_on_same_stop(record_factory):
    a = record_factory(charge="21-707(a)")
    b = record_factory(charge="13-401(b)")
    assert record_key(a) != record_key(b)
    assert record_key(a) == record_key(record_factory(charge=" 21-707(A) "))


def test_mapping_fills_columns_omitted_by_socrata(record_factory):
    row = to_csv_columns([record_factory()])[0]
    assert "Search Type" in row and row["Search Type"] is None
    assert row["SeqID"].startswith("c2341716")
    assert row["VehicleType"] == "02 - Automobile"
    assert row["Date Of Stop"] == "2026-10-19"
    assert row["Geolocation"] == "(38.984993, -77.084001)"


def test_mapped_feed_records_run_through_existing_cleaner(record_factory):
    """Regression: feed-shaped rows must not crash the bulk-CSV cleaning pipeline."""
    rows = to_csv_columns([
        record_factory(),
        record_factory(seq_id="8ca56a44", latitude="0", longitude="0", geolocation=None,
                       make="FORD", year="2027"),
    ])
    df = process_traffic_violations_df(pd.DataFrame(rows))
    assert len(df) == 2
    assert df["Search_Type"].iloc[0] == "NOT APPLICABLE"
    assert pd.isna(df["Latitude"].iloc[1])        # (0,0) treated as missing
    assert df["Year"].iloc[1] == 2027             # next model year is valid
    assert df["Datetime_Of_Stop"].iloc[0] == pd.Timestamp("2026-10-19 18:21:00")
