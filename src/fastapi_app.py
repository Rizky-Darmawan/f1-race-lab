"""Serve the live grid as a Server-Sent Events stream."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.sse import EventSourceResponse

from src.subscriber import Subscriber


def create_app(subscriber: Subscriber) -> FastAPI:
    """Stream one shared MQTT listener to every client on `/timing`."""

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        task = asyncio.create_task(subscriber.listen())
        try:
            yield
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    app = FastAPI(lifespan=lifespan)

    @app.get("/timing", response_class=EventSourceResponse)
    async def timing() -> AsyncIterator[dict[str, object]]:
        async for payload in subscriber.events():
            yield payload

    return app
