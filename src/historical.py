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

    def _is_duration(self, value: Any) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    def _elapsed_seconds(self, row: dict, tick: datetime) -> float | None:
        date_start = row.get("date_start")
        if not isinstance(date_start, str):
            return None
        return (tick - datetime.fromisoformat(date_start)).total_seconds()

    def _clear_sector(self, row: dict, sector: int) -> None:
        row[f"duration_sector_{sector}"] = None
        row[f"segments_sector_{sector}"] = None

    def _mask_unfinished_sectors(self, row: dict, elapsed: float) -> bool:
        cumulative = 0.0
        sector_pending = False
        chain_broken = False
        for sector in (1, 2, 3):
            duration = row.get(f"duration_sector_{sector}")
            if sector_pending:
                self._clear_sector(row, sector)
                continue
            if chain_broken or not self._is_duration(duration):
                chain_broken = True
                continue
            cumulative += duration
            if elapsed < cumulative:
                self._clear_sector(row, sector)
                sector_pending = True
        return sector_pending

    def _mask_unfinished_lap(self, row: dict, elapsed: float, sector_pending: bool) -> None:
        lap_duration = row.get("lap_duration")
        if sector_pending or (self._is_duration(lap_duration) and elapsed < lap_duration):
            row["lap_duration"] = None

    def _mask_unfinished_timings(self, row: dict, tick: datetime) -> dict:
        masked = dict(row)
        elapsed = self._elapsed_seconds(masked, tick)
        if elapsed is None:
            return masked
        sector_pending = self._mask_unfinished_sectors(masked, elapsed)
        self._mask_unfinished_lap(masked, elapsed, sector_pending)
        return masked

    def call_api(self, date: str) -> Any | None:
        """Return each driver's latest lap as of `date`.

        Sector duration, sector segments, and lap duration stay None until
        `date` reaches the time that split would have been printed live.
        """
        try:
            url = self._parse_url(date)
            response = urlopen(url).read().decode("utf-8")
            data = json.loads(response)
            latest = self._get_latest_data_for_each_driver(data)
            tick = datetime.fromisoformat(date)
            return [self._mask_unfinished_timings(row, tick) for row in latest]
        except URLError, TimeoutError, json.JSONDecodeError, UnicodeError:
            return None


if __name__ == "__main__":
    lap_date = "2026-03-29T06:10:00.000000+00:00"
    lap = LapHistorical(11253)
    data = lap.call_api(lap_date)
    print(data)
