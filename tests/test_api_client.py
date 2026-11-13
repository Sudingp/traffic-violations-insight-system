"""Tests for the live feed client: paging, retries, and error handling."""

import pytest
import requests

from src.api_client import FeedError, TrafficViolationsClient


def make_client(session, **kw):
    sleeps = []
    client = TrafficViolationsClient(session=session, sleep=sleeps.append, **kw)
    return client, sleeps


def test_pages_until_short_page(fake_session, ok, record_factory):
    pages = [[record_factory(seq_id=f"a{i}") for i in range(2)],
             [record_factory(seq_id=f"b{i}") for i in range(2)],
             [record_factory(seq_id="c0")]]
    session = fake_session([ok(p) for p in pages])
    client, _ = make_client(session, page_size=2)

    got = list(client.fetch_since("2026-10-01"))

    assert [len(p) for p in got] == [2, 2, 1]
    assert [c["$offset"] for c in session.calls] == [0, 2, 4]
    assert session.calls[0]["$where"] == "date_of_stop >= '2026-10-01T00:00:00'"
    assert session.calls[0]["$order"] == "date_of_stop ASC, :id ASC"


def test_exclusive_window(fake_session, ok):
    session = fake_session([ok([])])
    client, _ = make_client(session)
    list(client.fetch_since("2026-10-01", inclusive=False))
    assert session.calls[0]["$where"] == "date_of_stop > '2026-10-01T00:00:00'"


def test_empty_feed_yields_nothing(fake_session, ok):
    client, _ = make_client(fake_session([ok([])]))
    assert list(client.fetch_since("2026-10-01")) == []


def test_retries_transient_errors_then_succeeds(fake_session, ok, http_error, conn_error, record_factory):
    session = fake_session([
        conn_error,
        requests.Timeout("read timed out"),
        http_error(503),
        ok([record_factory()]),
    ])
    client, sleeps = make_client(session, page_size=10)

    got = list(client.fetch_since("2026-10-01"))

    assert len(got[0]) == 1
    assert len(session.calls) == 4
    assert len(sleeps) == 3
    # exponential: ~1s, ~2s, ~4s (+ up to 1s jitter)
    assert 1 <= sleeps[0] < 2 and 2 <= sleeps[1] < 3 and 4 <= sleeps[2] < 5


def test_honours_retry_after_on_429(fake_session, ok, http_error):
    session = fake_session([http_error(429, headers={"Retry-After": "7"}), ok([])])
    client, sleeps = make_client(session)
    list(client.fetch_since("2026-10-01"))
    assert sleeps == [7.0]


def test_gives_up_after_max_attempts(fake_session, http_error):
    session = fake_session([http_error(502)] * 3)
    client, sleeps = make_client(session, max_attempts=3)
    with pytest.raises(FeedError, match="after 3 attempts"):
        list(client.fetch_since("2026-10-01"))
    assert len(sleeps) == 2  # no pointless sleep after the final attempt


def test_does_not_retry_client_errors(fake_session, http_error):
    session = fake_session([http_error(400, text="query.soql.no-such-column")])
    client, sleeps = make_client(session)
    with pytest.raises(FeedError, match="Non-retryable HTTP 400"):
        list(client.fetch_since("2026-10-01"))
    assert len(session.calls) == 1 and sleeps == []


def test_rejects_non_list_payload(fake_session, ok):
    client, _ = make_client(fake_session([ok({"error": True, "message": "oops"})]))
    with pytest.raises(FeedError, match="Expected a JSON list"):
        list(client.fetch_since("2026-10-01"))


def test_app_token_header(fake_session, monkeypatch):
    monkeypatch.setenv("SODA_APP_TOKEN", "tok123")
    session = fake_session([])
    TrafficViolationsClient(session=session)
    assert session.headers["X-App-Token"] == "tok123"
