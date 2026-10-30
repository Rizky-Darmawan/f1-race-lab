"""Two-second clock simulation with a parameterized ISO 8601 start time."""

import time
from datetime import UTC, datetime, timedelta

from src.historical import IntervalHistorical


class LiveSimulation:
    """Simulate a race by publishing race messages every two seconds."""

    _TICK = timedelta(seconds=1.5)

    def __init__(self, session_key: int) -> None:
        self._session_key = session_key

    def _format_iso8601(self, dt: datetime) -> str:
        return dt.isoformat(timespec="microseconds")

    def _publish_historical(self, lower: datetime, upper: datetime) -> None:
        lower_datetime = self._format_iso8601(lower)
        upper_datetime = self._format_iso8601(upper)
        intervals = IntervalHistorical(self._session_key)
        intervals = intervals.call_api(lower_datetime, upper_datetime)
        if intervals:
            print(intervals, flush=True)
            print("=" * 70)

    def run_clock(self, start: datetime) -> None:
        """Replay historical interval data every two seconds, starting at `start`."""
        origin = start if start.tzinfo is not None else start.replace(tzinfo=UTC)
        wall_origin = time.perf_counter()
        tick = 0
        previous_time = origin
        try:
            while True:
                tick += 1
                current_time = origin + (self._TICK * tick)
                self._publish_historical(previous_time, current_time)
                previous_time = current_time
                remaining = wall_origin + (tick * self._TICK.total_seconds()) - time.perf_counter()
                if remaining > 0:
                    time.sleep(remaining)
        except KeyboardInterrupt:
            return
