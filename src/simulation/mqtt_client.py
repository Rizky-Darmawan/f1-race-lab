"""Publish to the local broker from the synchronous race clock."""

import asyncio
import threading

from amqtt.client import MQTTClient

from mqtt_server import HOST, PORT

_BROKER_URI = f"mqtt://{HOST}:{PORT}"


class MqttClient:
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
