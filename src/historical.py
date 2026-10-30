"""Contains implementation to hit Open F1 historical data using specific dates and time"""

import json
import time
from datetime import datetime, timedelta
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen


class IntervalHistorical:
    """Wrapper for Open F1 interval endpoint"""

    _BASE_URL = "https://api.openf1.org/v1/intervals"
    _URL_FILTER = "?session_key={session_key}&date>{lower_date}&date<={upper_date}"

    def __init__(self, session_key: int) -> None:
        self._session_key = session_key

    def _parse_url(self, lower_date: str, upper_date: str) -> str:
        base = self._BASE_URL
        url_filter = self._URL_FILTER.format(
            session_key=self._session_key, lower_date=lower_date, upper_date=upper_date
        )
        return base + url_filter

    def call_api(self, lower_date: str, upper_date: str) -> Any | None:
        """Call the interval API based on given session key and date"""
        try:
            url = self._parse_url(lower_date, upper_date)
            response = urlopen(url).read().decode("utf-8")
            return json.loads(response)
        except URLError, TimeoutError, json.JSONDecodeError, UnicodeError:
            return None

    def measure_call(self) -> tuple[Any | None, float]:
        """Return the payload and how many seconds the call took."""
        started = time.perf_counter()
        data = self.call_api()
        return data, time.perf_counter() - started


class LapHistorical:
    """Wrapper for Open F1 lap endpoint"""

    _BASE_URL = "https://api.openf1.org/v1/laps"
    _URL_FILTER = "?session_key={session_key}&date_start>{lower_date}&date_start<={upper_date}"

    def __init__(self, session_key: int) -> None:
        self._session_key = session_key

    def _subtract_minute(self, iso_date: str, minute: int) -> str:
        parsed = datetime.fromisoformat(iso_date)
        shifted = parsed - timedelta(minutes=minute)
        return shifted.isoformat(timespec="microseconds")

    def _parse_url(self, date: str) -> str:
        minute_subtracted = 15
        upper_date = date
        lower_date = self._subtract_minute(upper_date, minute_subtracted)
        url_filter = self._URL_FILTER.format(
            session_key=self._session_key, lower_date=lower_date, upper_date=upper_date
        )
        return self._BASE_URL + url_filter

    def _get_latest_data_for_each_driver(self, data: list[dict]) -> list[dict]:
        latest = {}
        for row in data:
            driver_number = row.get("driver_number")
            date_start = row.get("date_start")
            if driver_number is None or not isinstance(date_start, str):
                continue
            started = datetime.fromisoformat(date_start)
            current = latest.get(driver_number)
            if current is None or started > datetime.fromisoformat(current["date_start"]):
                latest[driver_number] = row
        return list(latest.values())

    def call_api(self, date: str) -> Any | None:
        """Call the interval API based on given session key and date"""
        try:
            url = self._parse_url(date)
            response = urlopen(url).read().decode("utf-8")
            data = json.loads(response)
            return self._get_latest_data_for_each_driver(data)
        except URLError, TimeoutError, json.JSONDecodeError, UnicodeError:
            return None


if __name__ == "__main__":
    lap_date = "2026-03-29T06:50:00.000000+00:00"
    lap = LapHistorical(11253)
    data = lap.call_api(lap_date)
    print(len(data))
