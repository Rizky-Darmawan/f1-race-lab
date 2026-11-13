"""Subscribe to live race topics and apply each message to the driver grid."""

import asyncio
import json

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

    def _format_live_grid(self, live_grid: dict[int, LiveGrid], at: str) -> str:
        """Turn the raw grid into a timing tower in current race order.

        The lap is the one held by the driver in position 1. Every other row
        shows its gap to the car ahead. `at` is the message timestamp.
        """
        ordered = sorted(live_grid.values(), key=lambda row: (row.position, row.driver_number))
        if not ordered:
            return at
        leader = next((row for row in ordered if row.position == 1), ordered[0])
        name_width = max(len(row.driver_name) for row in ordered)
        lines = [f"{at}  LAP {leader.lap}"]
        for row in ordered:
            name = f"{row.driver_name:<{name_width}}"
            if row is leader:
                lines.append(f"{row.position:>2}  {name}".rstrip())
            else:
                lines.append(f"{row.position:>2}  {name}  {row.interval:+.3f}")
        return "\n".join(lines)

    async def _listen(self) -> None:
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
                print(self._format_live_grid(self._live_grid, at))
        finally:
            await client.disconnect()

    def run(self) -> None:
        """Apply received messages to the live grid until interrupted."""
        try:
            asyncio.run(self._listen())
        except KeyboardInterrupt:
            return
