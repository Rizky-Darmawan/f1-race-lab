"""Microsecond clock simulation with a parameterized ISO 8601 start time."""

import time
from datetime import UTC, datetime, timedelta

from src.historical.interval import Interval
from src.historical.lap import Lap


class LiveSimulation:
    """Simulate a race by publishing race messages every microsecond."""

    _TICK = timedelta(microseconds=1)

    def __init__(self, intervals: list[Interval], laps: list[Lap]) -> None:
        self._intervals = intervals
        self._laps = laps

    def _format_iso8601(self, dt: datetime) -> str:
        return dt.isoformat(timespec="microseconds")

    def _publish_intervals(self, iso_date: str, interval_lookup: dict[str, Interval]) -> None:
        result = interval_lookup.get(iso_date)
        if result:
            print(result)
            print("=" * 150)

    def _publish_laps(self, iso_date: str, lap_lookup: dict[str, Lap]) -> None:
        result = lap_lookup.get(iso_date)
        if result:
            print(result)
            print("=" * 150)

    def run_clock(self, start: datetime) -> None:
        """Replay historical interval data every microsecond, starting at `start`."""
        interval_lookup = {i.date: i for i in self._intervals}
        lap_lookup: dict[str, list[Lap]] = {}
        for lap in self._laps:
            lap_lookup.setdefault(lap.date_start, []).append(lap)
        origin = start if start.tzinfo is not None else start.replace(tzinfo=UTC)
        wall_origin = time.perf_counter()
        tick = 0
        try:
            while True:
                tick += 1
                current_time = origin + (self._TICK * tick)
                current_time_iso = self._format_iso8601(current_time)
                self._publish_intervals(current_time_iso, interval_lookup)
                self._publish_laps(current_time_iso, lap_lookup)
                remaining = wall_origin + (tick * self._TICK.total_seconds()) - time.perf_counter()
                if remaining > 0:
                    time.sleep(remaining)
        except KeyboardInterrupt:
            return
