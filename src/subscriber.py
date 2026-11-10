"""Subscribe to live race topics and print each received topic."""

import asyncio
from datetime import UTC, datetime

from amqtt.client import MQTTClient
from amqtt.mqtt.constants import QOS_0

from src.historical.position import PositionData
from src.historical.starting_grid import StartingGrid, StartingGridData

_CLIENT_ID = "f1-race-lab-subscriber"


class Subscriber:
    """Subscribe to the given topics and print each message topic."""

    def __init__(self, host: str, port: int, topics: list[str]) -> None:
        self._uri = f"mqtt://{host}:{port}"
        self._topics = topics
        self._grid_state: list[StartingGrid] = []

    def get_latest_grid_state(self, session_key: int, date: datetime) -> list[StartingGrid]:
        """Return the grid at the given replay time and keep it as the current state."""
        if date.tzinfo is None:
            date = date.replace(tzinfo=UTC)
        positions = PositionData(session_key).construct_positions_from_api()
        self._grid_state = StartingGridData(session_key, positions).create_latest_grid_position(
            date.isoformat(timespec="microseconds")
        )
        return self._grid_state

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
                if header is None or header.topic_name is None:
                    continue
                print(header.topic_name)
        finally:
            await client.disconnect()

    def run(self) -> None:
        """Print each received topic until interrupted."""
        try:
            asyncio.run(self._listen())
        except KeyboardInterrupt:
            return
