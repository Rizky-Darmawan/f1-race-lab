"""Publish one historical feed for a replay timestamp."""

import json
from dataclasses import asdict

from src.historical.interval import Interval
from src.historical.lap import Lap
from src.historical.position import Position
from src.simulation.mqtt_client import MqttClient

_INTERVAL_TOPIC = "interval"
_LAP_TOPIC = "lap"
_POSITION_TOPIC = "position"


class IntervalPublisher:
    """Publish interval rows keyed by their timestamp."""

    def __init__(self, intervals: list[Interval], mqtt: MqttClient) -> None:
        self._mqtt = mqtt
        self._lookup = self._create_lookup(intervals)

    def _create_lookup(self, intervals: list[Interval]) -> dict[str, list[Interval]]:
        lookup: dict[str, list[Interval]] = {}
        for interval in intervals:
            lookup.setdefault(interval.date, []).append(interval)
        return lookup

    def publish(self, iso_date: str) -> None:
        intervals = self._lookup.get(iso_date)
        if intervals is None:
            return
        for interval in intervals:
            self._mqtt.publish(_INTERVAL_TOPIC, json.dumps(asdict(interval)).encode())


class LapPublisher:
    """Publish lap snapshots keyed by when each snapshot should go out."""

    def __init__(self, laps: list[Lap], mqtt: MqttClient) -> None:
        self._mqtt = mqtt
        self._lookup = self._create_lookup(laps)

    def _create_lookup(self, laps: list[Lap]) -> dict[str, list[Lap]]:
        lookup: dict[str, list[Lap]] = {}
        for lap in laps:
            lookup.setdefault(lap.date_start, []).append(lap)
        return lookup

    def publish(self, iso_date: str) -> None:
        laps = self._lookup.get(iso_date)
        if laps is None:
            return
        for lap in laps:
            self._mqtt.publish(_LAP_TOPIC, json.dumps(asdict(lap)).encode())


class PositionPublisher:
    """Publish position changes keyed by their timestamp."""

    def __init__(self, positions: list[Position], mqtt: MqttClient) -> None:
        self._mqtt = mqtt
        self._lookup = self._create_lookup(positions)

    def _create_lookup(self, positions: list[Position]) -> dict[str, list[Position]]:
        lookup: dict[str, list[Position]] = {}
        for position in positions:
            lookup.setdefault(position.date, []).append(position)
        return lookup

    def publish(self, iso_date: str) -> None:
        positions = self._lookup.get(iso_date)
        if positions is None:
            return
        for position in positions:
            self._mqtt.publish(_POSITION_TOPIC, json.dumps(asdict(position)).encode())
