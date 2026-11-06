"""Start a local MQTT broker that keeps every session in memory.

Retained messages, subscriptions, and client sessions live only in this
process. Stopping it drops that state and writes nothing to disk.
"""

import asyncio
import logging

from amqtt.broker import Broker
from amqtt.contexts import BrokerConfig, ListenerConfig, ListenerType

HOST = "127.0.0.1"
PORT = 1883
logger = logging.getLogger("mqtt_server")


def build_config() -> BrokerConfig:
    return BrokerConfig(
        listeners={
            "default": ListenerConfig(
                type=ListenerType.TCP,
                bind=f"{HOST}:{PORT}",
            )
        },
        plugins={
            "amqtt.plugins.authentication.AnonymousAuthPlugin": {
                "allow_anonymous": True,
            },
        },
    )


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s %(message)s",
    )
    logging.getLogger("transitions").setLevel(logging.WARNING)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    broker = Broker(build_config(), loop=loop)

    async def serve() -> None:
        await broker.start()
        logger.info("MQTT broker listening on mqtt://%s:%s", HOST, PORT)
        logger.info("In-memory only. Stop this process and all broker state is gone.")
        await asyncio.Future()

    try:
        loop.run_until_complete(serve())
    except KeyboardInterrupt:
        loop.run_until_complete(broker.shutdown())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
