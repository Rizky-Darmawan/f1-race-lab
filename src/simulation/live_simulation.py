"""Microsecond clock simulation with a parameterized ISO 8601 start time."""

import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from src.historical.interval import Interval
from src.historical.lap import Lap
from src.historical.position import Position
from src.simulation.mqtt_client import MqttClient
from src.simulation.publisher import IntervalPublisher, LapPublisher, PositionPublisher


@dataclass(frozen=True)
class HistoricalPayload:
    """Interval, lap, and position rows loaded for one replay."""

    intervals: list[Interval]
    laps: list[Lap]
    positions: list[Position]


class LiveSimulation:
    """Simulate a race by publishing race messages every microsecond."""

    _TICK = timedelta(microseconds=1)

    def __init__(self, payload: HistoricalPayload) -> None:
        mqtt = MqttClient()
        self._mqtt = mqtt
        self._interval_publisher = IntervalPublisher(payload.intervals, mqtt)
        self._lap_publisher = LapPublisher(payload.laps, mqtt)
        self._position_publisher = PositionPublisher(payload.positions, mqtt)

    def _print(self, tick: int) -> None:
        if tick == 1:
            print("Publisher started..")

    def _format_iso8601(self, dt: datetime) -> str:
        return dt.isoformat(timespec="microseconds")

    def _publish_all(self, iso_date: str) -> None:
        self._interval_publisher.publish(iso_date)
        self._lap_publisher.publish(iso_date)
        self._position_publisher.publish(iso_date)

    def run_clock(self, start: datetime) -> None:
        """Replay historical interval data every microsecond, starting at `start`."""
        origin = start if start.tzinfo is not None else start.replace(tzinfo=UTC)
        wall_origin = time.perf_counter()
        tick = 0
        self._mqtt.connect()
        try:
            while True:
                tick += 1
                current_time = origin + (self._TICK * tick)
                current_time_iso = self._format_iso8601(current_time)
                self._publish_all(current_time_iso)
                self._print(tick)
                remaining = wall_origin + (tick * self._TICK.total_seconds()) - time.perf_counter()
                if remaining > 0:
                    time.sleep(remaining)
        except KeyboardInterrupt:
            return
        finally:
            self._mqtt.disconnect()
