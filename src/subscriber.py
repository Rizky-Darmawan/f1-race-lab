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

    def _update_live_grid(self, topic: str, raw: bytes | bytearray) -> None:
        """Write the field this topic owns onto the driver named in the payload."""
        if topic == _INTERVAL_TOPIC:
            interval = Interval(**json.loads(raw))
            row = self._live_grid.get(interval.driver_number)
            if row is not None and isinstance(interval.interval, (int, float)):
                row.interval = float(interval.interval)
        elif topic == _LAP_TOPIC:
            lap = Lap(**json.loads(raw))
            row = self._live_grid.get(lap.driver_number)
            if row is not None:
                row.lap = lap.lap_number
        elif topic == _POSITION_TOPIC:
            position = Position(**json.loads(raw))
            row = self._live_grid.get(position.driver_number)
            if row is not None:
                row.position = position.position

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
                self._update_live_grid(header.topic_name, payload.data)
                print(self._live_grid)
        finally:
            await client.disconnect()

    def run(self) -> None:
        """Apply received messages to the live grid until interrupted."""
        try:
            asyncio.run(self._listen())
        except KeyboardInterrupt:
            return
