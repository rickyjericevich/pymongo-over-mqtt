from gmqtt import Client
from gmqtt.mqtt.constants import SubAckReasonCode
import logging
import json
from bson import json_util
from .schema import RequestTopic, ResponseTopic
from .mongodb import MongodbClient
from pydantic import ValidationError

class Mqtt(Client):

    def __init__(self, base_topic: str, mongo_client: MongodbClient):
        self.base_topic = base_topic
        self.mongodb_client = mongo_client
        super().__init__(
            "mongodb-over-mqtt",
            logger=logging.getLogger(),
            maximum_packet_size=268435460
        )

    @staticmethod # static method
    def on_connect(self, flags, result_code, properties) -> None:
        logging.debug(f"Connected to MQTT Broker - {flags=}, {result_code=}, {properties=}")
        self.subscribe(self.base_topic, qos=SubAckReasonCode.QOS2)

    @staticmethod
    def on_subscribe(self, mid, qos, properties) -> None:
        logging.debug(f"Subscribed to topic {self.base_topic} - {mid=}, {qos=}, {properties=}")

    @staticmethod
    def on_disconnect(self, packet, exc=None) -> None:
        logging.debug(f"Disconnected from MQTT Broker - {packet=}, {exc=}")

    @staticmethod
    async def on_message(self, topic, payload, qos, properties):
        logging.debug(f"Got message from topic {topic} - {payload=}, {qos=}, {properties=}")
        
        body = {}
        try:
            body = json.loads(payload.decode("utf-8"), object_hook=json_util.object_hook) # use object_hook to rehydrate bson objects like objectId
        except json.decoder.JSONDecodeError as e:
            logging.warning("Could not parse message body - it is likely empty. Continuing with body={}")
        
        try:
            topic = RequestTopic.from_string(topic)
            try:
                result = await topic.pymongo_attrs.evaluate(self.mongodb_client, body)
                logging.debug(f"{result=}")

                response_topics = properties.get('response_topic', None)
                logging.debug(f"Original response topics: {response_topics}")
                if result is None or response_topics is None:
                    logging.warning("No result or response topics, not responding")
                else:
                    try:
                        response_topics = [ResponseTopic(value=topic) for topic in response_topics]
                        logging.debug(f"Validated response topics: {response_topics}")

                        if len(response_topics):
                            logging.debug(f"Responding to {len(response_topics)} topics with result")
                            json_out = json_util.dumps(result)
                            for topic in response_topics:
                                logging.debug(f"Publishing to response topic {topic}: {json_out}")
                                self.publish(
                                    topic.value,
                                    json_out,
                                    qos=SubAckReasonCode.QOS0, # fire & forget, no need to wait for ack since we are running on the backend
                                    # retain=True,
                                    # message_expiry_interval=120, # x seconds
                                    # content_type='json'
                                )
                        return 0
                    
                    except ValidationError as e:
                        logging.error(f"Error while validating response topics {response_topics}: {e}")

            except Exception as e:
                logging.error(f"Error while evaluating pymongo command with params {topic.pymongo_attrs}, {body=}: {e}")

        except ValidationError as e:
            logging.error(f"Error while validating message {topic=}: {e}")
