"""Replay historical race messages in real time from a given start."""

import time
from dataclasses import dataclass
from datetime import UTC, datetime

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
    """Publish race messages when their original timestamp comes due."""

    def __init__(self, payload: HistoricalPayload) -> None:
        mqtt = MqttClient()
        self._payload = payload
        self._mqtt = mqtt
        self._interval_publisher = IntervalPublisher(payload.intervals, mqtt)
        self._lap_publisher = LapPublisher(payload.laps, mqtt)
        self._position_publisher = PositionPublisher(payload.positions, mqtt)

    def _schedule(self, start: datetime) -> list[tuple[datetime, str]]:
        """Return timestamps after `start`, earliest first.

        A time shared by several feeds is listed once. Rows at `start` are
        already in the initial grid, so they are left out.
        """
        stamps = {row.date for row in self._payload.intervals}
        stamps.update(row.date_start for row in self._payload.laps)
        stamps.update(row.date for row in self._payload.positions)
        upcoming: list[tuple[datetime, str]] = []
        for stamp in stamps:
            when = datetime.fromisoformat(stamp)
            if when.tzinfo is None:
                when = when.replace(tzinfo=UTC)
            if when <= start:
                continue
            upcoming.append((when, stamp))
        upcoming.sort(key=lambda item: item[0])
        return upcoming

    def _publish_all(self, iso_date: str) -> None:
        self._interval_publisher.publish(iso_date)
        self._lap_publisher.publish(iso_date)
        self._position_publisher.publish(iso_date)

    def run_clock(self, start: datetime) -> None:
        """Replay messages after `start`, keeping race time on the wall clock."""
        origin = start if start.tzinfo is not None else start.replace(tzinfo=UTC)
        schedule = self._schedule(origin)
        wall_origin = time.perf_counter()
        self._mqtt.connect()
        print("Publisher started..")
        try:
            for when, stamp in schedule:
                remaining = (when - origin).total_seconds() - (time.perf_counter() - wall_origin)
                if remaining > 0:
                    time.sleep(remaining)
                self._publish_all(stamp)
        except KeyboardInterrupt:
            return
        finally:
            self._mqtt.disconnect()
