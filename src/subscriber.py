"""Subscribe to live race topics and apply each message to the driver grid."""

import asyncio
import json
from collections.abc import AsyncIterator

from amqtt.client import MQTTClient
from amqtt.mqtt.constants import QOS_0

from src.historical.interval import Interval
from src.historical.lap import Lap
from src.historical.position import Position
from src.initial_state import LiveGrid

_CLIENT_ID = "f1-race-lab-subscriber"
_INTERVAL_TOPIC = "interval"
_LAP_TOPIC = "lap"
_POSITION_TOPIC = "position"


class Subscriber:
    """Keep the live grid in step with interval, lap, and position messages."""

    def __init__(
        self,
        host: str,
        port: int,
        topics: list[str],
        live_grid: dict[int, LiveGrid],
    ) -> None:
        self._uri = f"mqtt://{host}:{port}"
        self._topics = topics
        self._live_grid = live_grid
        self._latest: dict[str, object] | None = None
        self._clients: list[asyncio.Queue[dict[str, object]]] = []

    def _update_live_grid(self, topic: str, raw: bytes | bytearray) -> str:
        """Write the field this topic owns onto the driver named in the payload.

        Returns the timestamp carried by the message.
        """
        if topic == _INTERVAL_TOPIC:
            interval = Interval(**json.loads(raw))
            row = self._live_grid.get(interval.driver_number)
            if row is not None and isinstance(interval.interval, (int, float)):
                row.interval = float(interval.interval)
            return interval.date
        if topic == _LAP_TOPIC:
            lap = Lap(**json.loads(raw))
            row = self._live_grid.get(lap.driver_number)
            if row is not None:
                row.lap = lap.lap_number
            return lap.date_start
        if topic == _POSITION_TOPIC:
            position = Position(**json.loads(raw))
            row = self._live_grid.get(position.driver_number)
            if row is not None:
                row.position = position.position
            return position.date
        return ""

    def _format_live_grid(self, live_grid: dict[int, LiveGrid], at: str) -> dict[str, object]:
        """Turn the raw grid into a timing tower in current race order.

        The lap is the one held by the driver in position 1. That driver's
        interval is null; every other row shows its gap to the car ahead.
        `at` is the message timestamp.
        """
        ordered = sorted(live_grid.values(), key=lambda row: (row.position, row.driver_number))
        if not ordered:
            return {"at": at, "lap": None, "rows": []}
        leader = next((row for row in ordered if row.position == 1), ordered[0])
        rows = [
            {
                "position": row.position,
                "driver_number": row.driver_number,
                "driver_name": row.driver_name,
                "interval": None if row is leader else row.interval,
            }
            for row in ordered
        ]
        return {"at": at, "lap": leader.lap, "rows": rows}

    def _publish(self, at: str) -> None:
        """Store the formatted grid and hand the same payload to every client."""
        payload = self._format_live_grid(self._live_grid, at)
        self._latest = payload
        for client in self._clients:
            client.put_nowait(payload)

    def publish_snapshot(self, at: str) -> None:
        """Record the current grid so a client connecting now receives it."""
        self._publish(at)

    async def events(self) -> AsyncIterator[dict[str, object]]:
        """Yield the latest tower, then each later update, until the client leaves."""
        client: asyncio.Queue[dict[str, object]] = asyncio.Queue()
        self._clients.append(client)
        latest = self._latest
        try:
            if latest is not None:
                yield latest
            while True:
                yield await client.get()
        finally:
            self._clients.remove(client)

    async def listen(self) -> None:
        client = MQTTClient(_CLIENT_ID)
        await client.connect(self._uri)
        try:
            await client.subscribe([(topic, QOS_0) for topic in self._topics])
            while True:
                message = await client.deliver_message()
                if message is None or message.publish_packet is None:
                    continue
                header = message.publish_packet.variable_header
                payload = message.publish_packet.payload
                if (
                    header is None
                    or header.topic_name is None
                    or payload is None
                    or payload.data is None
                ):
                    continue
                at = self._update_live_grid(header.topic_name, payload.data)
                self._publish(at)
        finally:
            await client.disconnect()
