"""Microsecond clock simulation with a parameterized ISO 8601 start time."""

import asyncio
import json
import threading
import time
from dataclasses import dataclass, asdict
from datetime import UTC, datetime, timedelta

from amqtt.client import MQTTClient

from mqtt_server import HOST, PORT
from src.historical.interval import Interval
from src.historical.lap import Lap
from src.historical.position import Position

INTERVAL_TOPIC = "interval"
LAP_TOPIC = "lap"
POSITION_TOPIC = "position"
_BROKER_URI = f"mqtt://{HOST}:{PORT}"


class _MqttClient:
    """Publish to the local broker from the synchronous race clock."""

    def __init__(self) -> None:
        self._client: MQTTClient | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None

    def _run_loop(self, loop: asyncio.AbstractEventLoop, started: threading.Event) -> None:
        asyncio.set_event_loop(loop)
        loop.call_soon(started.set)
        loop.run_forever()

    async def _open(self) -> MQTTClient:
        client = MQTTClient("f1-race-lab")
        await client.connect(_BROKER_URI)
        return client

    def connect(self) -> None:
        loop = asyncio.new_event_loop()
        started = threading.Event()
        thread = threading.Thread(
            target=self._run_loop,
            args=(loop, started),
            name="mqtt-client",
            daemon=True,
        )
        thread.start()
        started.wait()
        self._loop = loop
        self._thread = thread
        try:
            self._client = asyncio.run_coroutine_threadsafe(self._open(), loop).result()
        except Exception:
            self.disconnect()
            raise

    def disconnect(self) -> None:
        client = self._client
        loop = self._loop
        thread = self._thread
        self._client = None
        self._loop = None
        self._thread = None
        if client is not None and loop is not None and loop.is_running():
            asyncio.run_coroutine_threadsafe(client.disconnect(), loop).result()
        if loop is not None and loop.is_running():
            loop.call_soon_threadsafe(loop.stop)
        if thread is not None:
            thread.join(timeout=2)

    def publish(self, topic: str, payload: bytes) -> None:
        if self._client is None or self._loop is None:
            return
        result = asyncio.run_coroutine_threadsafe(
            self._client.publish(topic, payload),
            self._loop,
        )
        result.result()


@dataclass(frozen=True)
class HistoricalPayload:
    intervals: list[Interval]
    laps: list[Lap]
    positions: list[Position]


@dataclass(frozen=True)
class Lookup:
    intervals: dict[str, list[Interval]]
    laps: dict[str, list[Lap]]
    positions: dict[str, list[Position]]


class LiveSimulation:
    """Simulate a race by publishing race messages every microsecond."""

    _TICK = timedelta(microseconds=1)

    def __init__(self, payload: HistoricalPayload) -> None:
        self._intervals = payload.intervals
        self._laps = payload.laps
        self._positions = payload.positions
        self._mqtt = _MqttClient()

    def _print(self, tick: int) -> None:
        if tick == 1:
            print("Publisher started..")

    def _format_iso8601(self, dt: datetime) -> str:
        return dt.isoformat(timespec="microseconds")

    def _publish_intervals(self, iso_date: str, interval_lookup: dict[str, list[Interval]]) -> None:
        intervals = interval_lookup.get(iso_date)
        if intervals is None:
            return
        for interval in intervals:
            self._mqtt.publish(INTERVAL_TOPIC, json.dumps(asdict(interval)).encode())

    def _publish_laps(self, iso_date: str, lap_lookup: dict[str, list[Lap]]) -> None:
        laps = lap_lookup.get(iso_date)
        if laps is None:
            return
        for lap in laps:
            self._mqtt.publish(LAP_TOPIC, json.dumps(asdict(lap)).encode())

    def _publish_position(self, iso_date: str, position_lookup: dict[str, list[Position]]) -> None:
        positions = position_lookup.get(iso_date)
        if positions is None:
            return
        for position in positions:
            self._mqtt.publish(POSITION_TOPIC, json.dumps(asdict(position)).encode())

    def _create_lookup(self) -> Lookup:
        interval_lookup: dict[str, list[Interval]] = {}
        for interval in self._intervals:
            interval_lookup.setdefault(interval.date, []).append(interval)
        lap_lookup: dict[str, list[Lap]] = {}
        for lap in self._laps:
            lap_lookup.setdefault(lap.date_start, []).append(lap)
        position_lookup: dict[str, list[Position]] = {}
        for position in self._positions:
            position_lookup.setdefault(position.date, []).append(position)
        return Lookup(interval_lookup, lap_lookup, position_lookup)

    def _publish_all(self, iso_date: str, lookup: Lookup) -> None:
        self._publish_intervals(iso_date, lookup.intervals)
        self._publish_laps(iso_date, lookup.laps)
        self._publish_position(iso_date, lookup.positions)

    def run_clock(self, start: datetime) -> None:
        """Replay historical interval data every microsecond, starting at `start`."""
        lookup_data = self._create_lookup()
        origin = start if start.tzinfo is not None else start.replace(tzinfo=UTC)
        wall_origin = time.perf_counter()
        tick = 0
        self._mqtt.connect()
        try:
            while True:
                tick += 1
                current_time = origin + (self._TICK * tick)
                current_time_iso = self._format_iso8601(current_time)
                self._publish_all(current_time_iso, lookup_data)
                self._print(tick)
                remaining = wall_origin + (tick * self._TICK.total_seconds()) - time.perf_counter()
                if remaining > 0:
                    time.sleep(remaining)
        except KeyboardInterrupt:
            return
        finally:
            self._mqtt.disconnect()
