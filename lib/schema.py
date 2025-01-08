from typing import Optional, Awaitable, Literal, ClassVar, Self
from pydantic import BaseModel, Field, ValidationError, field_validator
from enum import Enum
from lib.mongodb import MongodbClient
import logging


class SupportedMongoOperations(str, Enum):
    FIND = "find"
    AGGREGATE = "aggregate"
    INSERT_ONE = "insert_one"
    UPDATE_ONE = "update_one"
    # TODO: complete this enum


class BaseTopic(BaseModel):
    value: str = Field(min_length=1)

    @field_validator('value', mode='after')
    @staticmethod
    def _parse_value(value: str) -> str:
        if value.count("+"):
            raise ValueError(f"The base topic must not contain single-level wildcards")

        if value.count("#") > 1 or -1 < value.find("#") < len(value) - 1:
            raise ValueError(f"The base topic can only have one multi-level wildcard and it must be the last character in the topic")

        # ensure that value ends with "/#"

        if value.endswith("/"):
            return value + "#"

        return value.removesuffix("/#") + "/#"

    def without_wildcard(self) -> str:
        return self.value.removesuffix("/#")


class PymongoClientAttrs(BaseModel):
    database_name: str
    collection_name: Optional[str] = None
    mongodb_operator: SupportedMongoOperations | str


class DefaultOperationHandler(PymongoClientAttrs):
    def evaluate(self, client: MongodbClient, method_kwargs: dict): # -> Awaitable | Mongo Cursor:
        for attr in self.model_dump(exclude_none=True).values():
            client = getattr(client, attr) # client var gets overwritten with value returned by getattrs()

        return client(**method_kwargs) # client should be the final method that is operating on the db/collection


class CursorHandler(DefaultOperationHandler):
    mongodb_operator: Literal[SupportedMongoOperations.FIND] | Literal[SupportedMongoOperations.AGGREGATE] # TODO: add the other operations here that return cursors
    def evaluate(self, client: MongodbClient, method_kwargs: dict) -> Awaitable:
        mongo_cursor = super().evaluate(client, method_kwargs)
        return mongo_cursor.to_list(length=None)


class CoroutineHandler(DefaultOperationHandler):
    def evaluate(self, client: MongodbClient, method_kwargs: dict) -> Awaitable:
        return super().evaluate(client, method_kwargs)


class RequestTopic(BaseModel):
    base_topic: str
    pymongo_attrs: CursorHandler | CoroutineHandler
    remainder: Optional[str] = None

    def __init__(self, topic: str, *args, **kwargs):
        base_topic, db_name, *topic_rem = topic.split("/")
        topic_rem = list(filter(lambda s: s, topic_rem)) # remove falsey elements from list

        try:
            pymongo_attrs = {
                "database_name": db_name,
                "mongodb_operator": topic_rem.pop(0),
            }
        except IndexError as e:
            raise ValueError(f"Expected Request topic to be of the form 'BASE_TOPIC/collection_name/operation' but got '{topic}'") from e

        if len(topic_rem) >= 1:
            op, *topic_rem = topic_rem
            pymongo_attrs.update({
                "collection_name": pymongo_attrs["mongodb_operator"],
                "mongodb_operator": op,
            })
            topic_rem = "/".join(topic_rem)

        super().__init__(
            base_topic=base_topic,
            pymongo_attrs=pymongo_attrs,
            remainder=topic_rem if topic_rem else None,
            *args, **kwargs
        )


class ResponseTopic(BaseModel):
    value: str = Field(min_length=1)

    prohibited_base_topic: ClassVar[BaseTopic]

    @field_validator('value', mode='after')
    @classmethod
    def _contains_prohibited_base_topic(cls, value: str) -> str:
        if value.startswith(cls.prohibited_base_topic.without_wildcard()):
            raise ValueError(f'Response Topic may not start with the value of BASE_TOPIC={cls.prohibited_base_topic}')
        return value

    @classmethod
    def parse_string_list(cls, topics: list[str]) -> list[Self]:
        if topics is None or len(topics) == 0:
            return []

        for i in range(len(topics)-1, -1, -1):
            try:
                topics[i] = ResponseTopic(value=topics[i])
            except ValidationError as e:
                logging.warning(f"Ignoring invalid response topic ({topics[i]})")
                logging.exception(e)
                del topics[i]

        return topics
