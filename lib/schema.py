from typing import Any, Optional, Awaitable, Literal# , Self # uncomment this when support python 3.11
from pydantic import BaseModel, Field, ValidationError
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
    value: str = Field()

    def strip_wildcards(self) -> str:
        return self.val.split("/#")[0].split("/+")[0]

    def with_multilevel_wildcard(self) -> str:
        return self.val + "/#"

    def __str__(self) -> str:
        return self.val


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
    
    @classmethod
    def from_string(cls, topic: str):# -> Self:
        base_topic, db_name, *topic_rem = topic.split("/")
        topic_rem = list(filter(lambda s: s, topic_rem)) # remove falsey elements from list

        try:
            pymongo_attrs = {
                "database_name": db_name,
                "mongodb_operator": topic_rem.pop(0),
            }

            if len(topic_rem) >= 1:
                op, *topic_rem = topic_rem
                pymongo_attrs.update({
                    "collection_name": pymongo_attrs["mongodb_operator"],
                    "mongodb_operator": op,
                })
                topic_rem = "/".join(topic_rem)

            return cls(
                base_topic=base_topic,
                pymongo_attrs=pymongo_attrs,
                remainder=topic_rem if topic_rem else None
            )
        except IndexError as e:
            raise ValidationError() # TODO handle case where topic_rem.pop(0) errors


class ResponseTopic(BaseModel):
    value: str = Field(min_length=1)
    # def __init__(self, prohibited_base_topic:str, response_topic: str):
    #     if not response_topic or response_topic.startswith(prohibited_base_topic):
    #         raise ValidationError() # TODO populate exception object
        
