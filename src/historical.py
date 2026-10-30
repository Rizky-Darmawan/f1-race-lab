"""Contains implementation to hit Open F1 historical data using specific dates and time"""

import json
import time
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen


class IntervalHistorical:
    """Wrapper for Open F1 interval endpoint"""

    _BASE_URL = "https://api.openf1.org/v1/intervals"
    _URL_FILTER = "?session_key={session_key}&date>{lower_date}&date<={upper_date}"

    def __init__(self, session_key: int, lower_date: str, upper_date: str) -> None:
        self._session_key = session_key
        self._lower_date = lower_date
        self._upper_date = upper_date

    def _parse_url(self) -> str:
        base = self._BASE_URL
        url_filter = self._URL_FILTER.format(
            session_key=self._session_key, lower_date=self._lower_date, upper_date=self._upper_date
        )
        return base + url_filter

    def call_api(self) -> Any | None:
        """Call the interval API based on given session key and date"""
        try:
            url = self._parse_url()
            response = urlopen(url).read().decode("utf-8")
            return json.loads(response)
        except URLError, TimeoutError, json.JSONDecodeError, UnicodeError:
            return None

    def measure_call(self) -> tuple[Any | None, float]:
        """Return the payload and how many seconds the call took."""
        started = time.perf_counter()
        data = self.call_api()
        return data, time.perf_counter() - started


if __name__ == "__main__":
    lower_bound_date = "2026-03-29T06:31:57.000000+00:00"
    upper_bound_date = "2026-03-29T06:31:58.000000+00:00"
    interval = IntervalHistorical(11253, lower_bound_date, upper_bound_date)
    data = interval.call_api()
    print(data)
