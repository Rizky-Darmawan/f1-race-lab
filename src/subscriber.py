"""Subscribe to live race topics and print each received topic."""

import asyncio

from amqtt.client import MQTTClient
from amqtt.mqtt.constants import QOS_0

from src.initial_state import LiveGrid

_CLIENT_ID = "f1-race-lab-subscriber"


class Subscriber:
    """Subscribe to the given topics and print each message topic."""

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
