import asyncio
from os import getenv
import signal
import logging
import uvloop
from lib.mongodb import MongodbClient
from lib.mqtt import Mqtt as MqttClient


LOG_LEVEL = getenv("LOG_LEVEL", "DEBUG")
BROKER_HOST = getenv("BROKER_HOST", "localhost")
MQTT_PORT = int(getenv("MQTT_PORT", 1883))
MONGODB_URI = getenv("MONGODB_URI", "mongodb://localhost:27017")
BASE_TOPIC = getenv("BASE_TOPIC", "mongodb/#")


asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
STOP = asyncio.Event()


async def main():
    mongo_client = MongodbClient(MONGODB_URI)
    await mongo_client.ensure_connection()

    mqtt_client = MqttClient(BASE_TOPIC, mongo_client)
    # mqtt_client.set_auth_credentials(token, None)
    await mqtt_client.connect(BROKER_HOST, MQTT_PORT)

    await STOP.wait() # blocks forever until a SIG occurs

    await mqtt_client.disconnect()
    await mongo_client.close()


if __name__ == "__main__":
    logging.basicConfig(level=LOG_LEVEL) # see https://docs.python.org/3/library/logging.html#levels

    loop = asyncio.new_event_loop()
    loop.add_signal_handler(signal.SIGINT, STOP.set) # exit the event loop
    loop.add_signal_handler(signal.SIGTERM, STOP.set)

    loop.run_until_complete(main())
