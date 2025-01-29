from paho.mqtt.client import Client, CallbackAPIVersion, MQTTv5
from paho.mqtt.properties import Properties
from paho.mqtt.packettypes import PacketTypes
from bson import json_util
from threading import Timer


BROKER = "localhost"
PORT = 1883
BASE_TOPIC = "mongodb"
DB_NAME = "test_db"
COLLECTION_NAME = "test_collection"
PYMONGO_COMMAND = "find"
MESSAGE = {"filter": {}, "skip": 1, "limit": 1} # arguments for find command
RESPONSE_TOPIC = "test/response" # topic that receives the output of the PyMongo command
CLIENT_ID = "paho_python_client"
TIMEOUT = 5 # seconds


def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Connected to broker with reason code: {reason_code}")
    client.subscribe(RESPONSE_TOPIC)


def on_subscribe(client, userdata, mid, reason_code_list, properties):
    print(f"Subscribed to response topic: {RESPONSE_TOPIC}")

    topic = f"{BASE_TOPIC}/{DB_NAME}/{COLLECTION_NAME}/{PYMONGO_COMMAND}"
    payload = json_util.dumps(MESSAGE) # convert dictionary to valid mongo json string
    properties = Properties(PacketTypes.PUBLISH)
    properties.ResponseTopic = RESPONSE_TOPIC # include the response topic in the message properties

    print(f"Publishing message to {topic=}, {payload=}")
    client.publish(topic=topic, payload=payload, properties=properties)


def on_message(client, userdata, msg):
    response = json_util.loads(msg.payload.decode()) # rehydrate bson objects like objectId
    print(f"Received message from response topic: {response}")
    timer.cancel()


print(f"Connecting to broker {BROKER}:{PORT}...")

client = Client(CallbackAPIVersion.VERSION2, client_id=CLIENT_ID, protocol=MQTTv5)
client.on_connect = on_connect
client.on_subscribe = on_subscribe
client.on_message = on_message
client.connect(BROKER, PORT)
client.loop_start()

timer = Timer(TIMEOUT, lambda: print(f"No message received from response topic after {TIMEOUT}s. Program terminating."))
timer.start()
timer.join()

client.loop_stop()
client.disconnect()