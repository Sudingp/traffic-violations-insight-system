"""
Shared fixtures for the live-ingestion tests.

The sample records mirror the real shape of the county's SODA API
(field names, floating timestamps, geolocation objects, and null
fields omitted entirely) so tests catch the same problems the live
feed would cause.
"""

import copy

import pytest
import requests


def make_record(**overrides):
    rec = {
        "seq_id": "c2341716-38f5-4bd6-af71-bc1bf05766d4",
        "date_of_stop": "2026-10-19T00:00:00.000",
        "time_of_stop": "18:21:00",
        "agency": "MCP",
        "subagency": "2nd District, Bethesda",
        "description": "DRIVER FAILURE TO STOP AT STOP SIGN LINE",
        "location": "LELAND ST/MAPLE AVE",
        "latitude": "38.984993",
        "longitude": "-77.084001",
        "accident": "No",
        "belts": "No",
        "personal_injury": "No",
        "property_damage": "No",
        "fatal": "No",
        "commercial_license": "No",
        "hazmat": "No",
        "commercial_vehicle": "No",
        "alcohol": "No",
        "work_zone": "No",
        # search_* fields intentionally absent: Socrata omits null fields
        "state": "MD",
        "vehicle_type": "02 - Automobile",
        "year": "2018",
        "make": "VOLKS",
        "model": "JETTA",
        "color": "BLUE, DARK",
        "violation_type": "Warning",
        "charge": "21-707(a)",
        "article": "Transportation Article",
        "contributed_to_accident": "false",
        "race": "WHITE",
        "gender": "F",
        "driver_city": "SILVER SPRING",
        "driver_state": "MD",
        "dl_state": "CA",
        "arrest_type": "A - Marked Patrol",
        "geolocation": {"latitude": "38.984993", "longitude": "-77.084001"},
        ":@computed_region_vu5j_pcmz": "1",
    }
    rec.update(overrides)
    return {k: v for k, v in rec.items() if v is not None}


@pytest.fixture
def record_factory():
    return make_record


class FakeResponse:
    def __init__(self, status_code=200, payload=None, headers=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}
        self.text = text

    def json(self):
        return copy.deepcopy(self._payload)


class FakeSession:
    """Plays back a scripted list of responses/exceptions, records calls."""

    def __init__(self, script):
        self.script = list(script)
        self.calls = []
        self.headers = {}

    def get(self, url, params=None, timeout=None):
        self.calls.append(dict(params or {}))
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


@pytest.fixture
def fake_session():
    return FakeSession


@pytest.fixture
def ok():
    return lambda payload: FakeResponse(200, payload)


@pytest.fixture
def http_error():
    return lambda code, **kw: FakeResponse(code, None, **kw)


@pytest.fixture
def conn_error():
    return requests.ConnectionError("connection reset")
