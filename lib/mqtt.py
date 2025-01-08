from gmqtt import Client
from gmqtt.mqtt.constants import SubAckReasonCode
import logging
import json
from bson import json_util
from .schema import BaseTopic, RequestTopic, ResponseTopic
from .mongodb import MongodbClient
from pydantic import ValidationError
from typing import Self

class Mqtt(Client):

    def __init__(self, base_topic: BaseTopic, mongo_client: MongodbClient):
        self.base_topic = base_topic
        self.mongodb_client = mongo_client
        super().__init__(
            "pymongo-over-mqtt",
            logger=logging.getLogger(),
            maximum_packet_size=268435460
        )


    @staticmethod # static method
    def on_connect(self: Self, flags, result_code, properties) -> None:
        logging.debug(f"Connected to MQTT Broker - {flags=}, {result_code=}, {properties=}")
        self.subscribe(self.base_topic.value, qos=SubAckReasonCode.QOS2)


    @staticmethod
    def on_subscribe(self: Self, mid, qos, properties) -> None:
        logging.debug(f"Subscribed to topic {self.base_topic.value} - {mid=}, {qos=}, {properties=}")


    @staticmethod
    def on_disconnect(self: Self, packet, exc=None) -> None:
        logging.debug(f"Disconnected from MQTT Broker - {packet=}, {exc=}")


    @staticmethod
    async def on_message(self: Self, topic, payload, qos, properties):
        logging.debug(f"Got message from topic {topic} - {payload=}, {qos=}, {properties=}")
        
        body = {}
        try:
            body = json.loads(payload.decode("utf-8"), object_hook=json_util.object_hook) # use object_hook to rehydrate bson objects like objectId
        except json.decoder.JSONDecodeError as e:
            logging.warning("Could not parse message body - it is likely empty. Continuing with body={}")

        try:
            topic = RequestTopic(topic)
            logging.debug(f"request_{topic=}")

            result = await topic.pymongo_attrs.evaluate(self.mongodb_client, body)
            logging.debug(f"{result=}")

            ResponseTopic.prohibited_base_topic = self.base_topic # TODO: figure out a better way for ResponseTopic to have access to self.base_topic
            response_topics = ResponseTopic.parse_string_list(properties.get('response_topic'))
            if result is None or not len(response_topics):
                logging.warning("No result or valid response topics, not responding")
            else:
                json_out = json_util.dumps(result)
                logging.debug(f"Publishing to response topics {response_topics}: {json_out}")
                for topic in response_topics:
                    self.publish(
                        topic.value,
                        json_out,
                        qos=SubAckReasonCode.QOS0, # fire & forget, no need to wait for ack since we are running on the backend
                        # retain=True,
                        # message_expiry_interval=120, # x seconds
                        # content_type='json'
                    )

                return 0

        except (ValidationError, Exception) as e:
            logging.exception(e)
