import asyncio
from typing import Optional, Literal, ClassVar, Self
from pydantic import BaseModel, Field, ValidationError, field_validator
from enum import Enum
from motor.motor_asyncio import AsyncIOMotorCursor
from lib.mongodb import MongodbClient
import logging


class SupportedPyMongoOperations(str, Enum):
    # Database level ops https://pymongo.readthedocs.io/en/stable/api/pymongo/database.html
    # __GETITEM__ = "__getitem__"
    # __GETATTR__ = "__getattr__"
    # AGGREGATE = "aggregate"
    # COMMAND = "command"
    # CREATE_COLLECTION = "create_collection"
    # CURSOR_COMMAND = "cursor_command"
    # DERFERENCE = "dereference"
    DROP_COLLECTION = "drop_collection"
    # GET_COLLECTION = "get_collection"
    LIST_COLLECTION_NAMES = "list_collection_names"
    # LIST_COLLECTIONS = "list_collections"
    # VALIDATE_COLLECTION = "validate_collection"
    # WATCH = "watch"
    # WITH_OPTIONS = "with_options"

    # Collection level ops https://pymongo.readthedocs.io/en/stable/api/pymongo/collection.html
    # WITH_OPTIONS = "with_options"
    # BULK_WRITE = "bulk_write"
    INSERT_ONE = "insert_one"
    INSERT_MANY = "insert_many"
    REPLACE_ONE = "replace_one"
    UPDATE_ONE = "update_one"
    UPDATE_MANY = "update_many"
    DELETE_ONE = "delete_one"
    DELETE_MANY = "delete_many"
    # AGGREGATE = "aggregate"
    # AGGREGATE_RAW_BATCHES = "aggregate_raw_batches"
    # WATCH = "watch"
    FIND = "find"
    # FIND_RAW_BATCHES = "find_raw_batches"
    FIND_ONE = "find_one"
    FIND_ONE_AND_DELETE = "find_one_and_delete"
    FIND_ONE_AND_REPLACE = "find_one_and_replace"
    FIND_ONE_AND_UPDATE = "find_one_and_update"
    COUNT_DOCUMENTS = "count_documents"
    ESTIMATED_DOCUMENT_COUNT = "estimated_document_count"
    # DISTINCT = "distinct"
    CREATE_INDEX = "create_index"
    CREATE_INDEXES = "create_indexes"
    DROP_INDEX = "drop_index"
    DROP_INDEXES = "drop_indexes"
    LIST_INDEXES = "list_indexes"
    INDEX_INFORMATION = "index_information"
    CREATE_SEARCH_INDEX = "create_search_index"
    CREATE_SEARCH_INDEXES = "create_search_indexes"
    DROP_SEARCH_INDEX = "drop_search_index"
    LIST_SEARCH_INDEXES = "list_search_indexes"
    UPDATE_SEARCH_INDEX = "update_search_index"
    DROP = "drop"
    RENAME = "rename"
    OPTIONS = "options"
    # __GETITEM__ = "__getitem__"
    # __GETATTR__ = "__getattr__"


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
    mongodb_operator: SupportedPyMongoOperations | str


class DefaultOperationHandler(PymongoClientAttrs):
    def evaluate(self, client: MongodbClient, method_kwargs: dict) -> asyncio.Future | AsyncIOMotorCursor:
        for attr in self.model_dump(exclude_none=True).values():
            client = getattr(client, attr) # client var gets overwritten with value returned by getattrs()

        return client(**method_kwargs) # client should be the final method that is operating on the db/collection


class CursorHandler(DefaultOperationHandler):
    mongodb_operator: Literal[SupportedPyMongoOperations.FIND] | Literal[SupportedPyMongoOperations.AGGREGATE] # TODO: add the other operations here that return cursors
    def evaluate(self, client: MongodbClient, method_kwargs: dict) -> asyncio.Future[list]:
        mongo_cursor: AsyncIOMotorCursor = super().evaluate(client, method_kwargs)
        return mongo_cursor.to_list(length=None)


class CoroutineHandler(DefaultOperationHandler):
    def evaluate(self, client: MongodbClient, method_kwargs: dict) -> asyncio.Future:
        return super().evaluate(client, method_kwargs)


class WriteResultHandler(DefaultOperationHandler):
    mongodb_operator: Literal[SupportedPyMongoOperations.INSERT_ONE]

    @staticmethod
    def get_write_result_properties(write_result) -> dict: # https://stackoverflow.com/a/65825416
        return {k: getattr(write_result, k) for kls in type(write_result).mro() for k, v in vars(kls).items() if isinstance(v, property)}

    async def evaluate(self, client: MongodbClient, method_kwargs: dict) -> asyncio.Future:
        write_result = await super().evaluate(client, method_kwargs)
        return self.get_write_result_properties(write_result)


class RequestTopic(BaseModel):
    base_topic: str
    pymongo_attrs: CursorHandler | WriteResultHandler | CoroutineHandler
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

        super().__init__( # TODO: use kwarg shortcuts when python 3.14 drops
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
        if not topics:
            return []

        for i in range(len(topics) - 1, -1, -1):
            try:
                topics[i] = ResponseTopic(value=topics[i])
            except ValidationError as e:
                logging.warning(f"Ignoring invalid response topic ({topics[i]})")
                logging.exception(e)
                del topics[i]

        return topics
