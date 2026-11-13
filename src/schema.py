"""
Schema validation for records coming from the live feed.

Each raw API record is validated before it touches the database:

* Hard failures (record is quarantined, never loaded):
  missing/blank seq_id, unparseable or future date_of_stop,
  missing description, malformed latitude/longitude.
* Schema drift (record is loaded, but a warning is logged):
  fields we have never seen before, e.g. the county adds a column.

The feed's field names (seq_id, vehicle_type, ...) differ from the bulk
CSV's headers (SeqID, VehicleType, ...). `to_csv_columns` maps between
them so the existing cleaning pipeline in preprocessing.py is reused
unchanged for both the bulk file and the live feed.
"""

import logging
from datetime import date, datetime
from typing import Dict, List, Optional, Set, Tuple

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

logger = logging.getLogger("tvis.schema")

# Live-feed field name -> bulk-CSV header expected by preprocessing.py
API_TO_CSV: Dict[str, str] = {
    "seq_id": "SeqID",
    "date_of_stop": "Date Of Stop",
    "time_of_stop": "Time Of Stop",
    "agency": "Agency",
    "subagency": "SubAgency",
    "description": "Description",
    "location": "Location",
    "latitude": "Latitude",
    "longitude": "Longitude",
    "accident": "Accident",
    "belts": "Belts",
    "personal_injury": "Personal Injury",
    "property_damage": "Property Damage",
    "fatal": "Fatal",
    "commercial_license": "Commercial License",
    "hazmat": "HAZMAT",
    "commercial_vehicle": "Commercial Vehicle",
    "alcohol": "Alcohol",
    "work_zone": "Work Zone",
    "search_conducted": "Search Conducted",
    "search_disposition": "Search Disposition",
    "search_outcome": "Search Outcome",
    "search_reason": "Search Reason",
    "search_reason_for_stop": "Search Reason For Stop",
    "search_type": "Search Type",
    "search_arrest_reason": "Search Arrest Reason",
    "state": "State",
    "vehicle_type": "VehicleType",
    "year": "Year",
    "make": "Make",
    "model": "Model",
    "color": "Color",
    "violation_type": "Violation Type",
    "charge": "Charge",
    "article": "Article",
    "contributed_to_accident": "Contributed To Accident",
    "race": "Race",
    "gender": "Gender",
    "driver_city": "Driver City",
    "driver_state": "Driver State",
    "dl_state": "DL State",
    "arrest_type": "Arrest Type",
    "geolocation": "Geolocation",
}
KNOWN_FIELDS: Set[str] = set(API_TO_CSV)


class ViolationRecord(BaseModel):
    """Minimum contract a feed record must satisfy to be loaded."""

    model_config = ConfigDict(extra="allow", str_strip_whitespace=True)

    seq_id: str
    date_of_stop: date
    description: str
    time_of_stop: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    charge: Optional[str] = None

    @field_validator("seq_id", "description")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v:
            raise ValueError("must not be blank")
        return v

    @field_validator("date_of_stop", mode="before")
    @classmethod
    def parse_floating_timestamp(cls, v):
        # Socrata returns floating timestamps like "2026-10-19T00:00:00.000"
        if isinstance(v, str) and "T" in v:
            return datetime.fromisoformat(v.replace("Z", "")).date()
        return v

    @field_validator("date_of_stop")
    @classmethod
    def not_in_future(cls, v: date) -> date:
        if v > date.today():
            raise ValueError(f"date_of_stop {v} is in the future")
        if v.year < 1990:
            raise ValueError(f"date_of_stop {v} is before 1990")
        return v


def record_key(raw: dict) -> str:
    """
    Natural key for one charge on one stop.

    A single stop (seq_id) can carry several charges, so seq_id alone is
    not unique. The combination below is what the dataset treats as a row.
    """
    parts = [raw.get(f, "") or "" for f in ("seq_id", "charge", "violation_type", "description")]
    return "|".join(str(p).strip().upper() for p in parts)


def validate_records(records: List[dict]) -> Tuple[List[dict], List[dict], Set[str]]:
    """
    Split raw records into (valid, rejected, unknown_fields).

    Rejected records carry the original payload plus the validation errors,
    so they can be inspected and replayed later.
    """
    valid, rejected = [], []
    unknown: Set[str] = set()

    for raw in records:
        # Socrata adds ":@computed_region_*" helper columns; they're not data drift.
        extra = {k for k in raw if k not in KNOWN_FIELDS and not k.startswith(":@")}
        unknown |= extra
        try:
            ViolationRecord.model_validate(raw)
        except ValidationError as exc:
            rejected.append({
                "record": raw,
                "errors": [
                    f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()
                ],
            })
            continue
        valid.append(raw)

    if unknown:
        logger.warning("Schema drift: feed returned unknown fields %s", sorted(unknown))
    return valid, rejected, unknown


def _flatten_geolocation(value) -> str:
    """Feed sends geolocation as an object; the CSV had a '(lat, lon)' string."""
    if isinstance(value, dict):
        lat, lon = value.get("latitude"), value.get("longitude")
        if lat is not None and lon is not None:
            return f"({lat}, {lon})"
        return ""
    return value if value is not None else ""


def to_csv_columns(records: List[dict]) -> List[dict]:
    """
    Rename feed fields to bulk-CSV headers and fill every expected column.

    Socrata omits null fields from the JSON entirely, so a page where no
    record had a search conducted has no 'search_type' key at all. Filling
    every column here keeps preprocessing.py from raising KeyError.
    """
    rows = []
    for raw in records:
        row = {csv_name: raw.get(api_name) for api_name, csv_name in API_TO_CSV.items()}
        row["Geolocation"] = _flatten_geolocation(raw.get("geolocation"))
        date_val = raw.get("date_of_stop")
        if isinstance(date_val, str) and "T" in date_val:
            # preprocessing.py parses the date; give it a plain date string
            row["Date Of Stop"] = date_val.split("T")[0]
        rows.append(row)
    return rows
