"""
Client for the live Montgomery County Traffic Violations feed.

Source: Montgomery County Open Data (Socrata SODA API), dataset 4mse-ku6q.
The county republishes this dataset daily, so it behaves like a partner
feed: it keeps growing, it can be slow or unavailable, and it can change
shape without warning.

Design notes
------------
* Pages through results with $limit/$offset, ordered by (date_of_stop, :id)
  so paging is stable while new rows are being added.
* Retries transient failures (timeouts, connection errors, 429 and 5xx)
  with exponential backoff + jitter, and honours the Retry-After header.
* Does NOT retry other 4xx errors: a 400 means our query is wrong, and
  retrying it would only hide the bug.
"""

import logging
import os
import random
import time
from typing import Callable, Iterator, List, Optional

import requests

logger = logging.getLogger("tvis.api")

DEFAULT_BASE_URL = "https://data.montgomerycountymd.gov/resource/4mse-ku6q.json"
RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class FeedError(Exception):
    """Raised when the feed cannot be read after all retries."""


class TrafficViolationsClient:
    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        app_token: Optional[str] = None,
        page_size: int = 5000,
        timeout: float = 30.0,
        max_attempts: int = 5,
        backoff_base: float = 2.0,
        session: Optional[requests.Session] = None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.base_url = base_url
        self.page_size = page_size
        self.timeout = timeout
        self.max_attempts = max_attempts
        self.backoff_base = backoff_base
        self.session = session or requests.Session()
        self._sleep = sleep  # injectable so tests don't actually wait

        token = app_token or os.environ.get("SODA_APP_TOKEN")
        if token:
            # Optional: an app token raises the county's rate limits.
            self.session.headers["X-App-Token"] = token

    # ------------------------------------------------------------------ #
    # Low-level request with retries
    # ------------------------------------------------------------------ #
    def _backoff_delay(self, attempt: int, retry_after: Optional[str]) -> float:
        if retry_after:
            try:
                return float(retry_after)
            except ValueError:
                pass
        # 1s, 2s, 4s, 8s ... plus up to 1s of jitter so parallel jobs don't sync up
        return self.backoff_base ** (attempt - 1) + random.uniform(0, 1)

    def _get(self, params: dict) -> List[dict]:
        last_error: Optional[str] = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                resp = self.session.get(self.base_url, params=params, timeout=self.timeout)
            except (requests.ConnectionError, requests.Timeout) as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                retry_after = None
            else:
                if resp.status_code == 200:
                    data = resp.json()
                    if not isinstance(data, list):
                        raise FeedError(f"Expected a JSON list, got {type(data).__name__}")
                    return data
                if resp.status_code not in RETRYABLE_STATUS:
                    raise FeedError(
                        f"Non-retryable HTTP {resp.status_code} from feed: {resp.text[:300]}"
                    )
                last_error = f"HTTP {resp.status_code}"
                retry_after = resp.headers.get("Retry-After")

            if attempt == self.max_attempts:
                break
            delay = self._backoff_delay(attempt, retry_after)
            logger.warning(
                "Feed request failed (%s), attempt %d/%d, retrying in %.1fs",
                last_error, attempt, self.max_attempts, delay,
            )
            self._sleep(delay)

        raise FeedError(f"Feed unavailable after {self.max_attempts} attempts: {last_error}")

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def fetch_since(self, since_date: str, inclusive: bool = True) -> Iterator[List[dict]]:
        """
        Yield pages of raw records with date_of_stop on/after `since_date` (YYYY-MM-DD).

        `inclusive=False` fetches strictly after that day; used on the first
        live run so we don't re-ingest the last day of the bulk CSV.
        """
        op = ">=" if inclusive else ">"
        where = f"date_of_stop {op} '{since_date}T00:00:00'"
        offset = 0
        page_no = 0
        while True:
            params = {
                "$where": where,
                "$order": "date_of_stop ASC, :id ASC",
                "$limit": self.page_size,
                "$offset": offset,
            }
            page = self._get(params)
            page_no += 1
            logger.info("Fetched page %d: %d records (offset %d)", page_no, len(page), offset)
            if not page:
                return
            yield page
            if len(page) < self.page_size:
                return
            offset += self.page_size
