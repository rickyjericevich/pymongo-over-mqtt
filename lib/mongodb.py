import motor.motor_asyncio as motor
import logging

class MongodbClient(motor.AsyncIOMotorClient):
    """A wrapper around Motor's AsyncIOMotorClient with an additional method ensure_connection()
    that, when called, blocks until the connection to the Mongo database is established
    """

    def __init__(self, mongodb_uri: str):
        logging.info(f"Connecting to mongo db at {mongodb_uri}")
        super().__init__(mongodb_uri)

    async def ensure_connection(self):
        # https://pymongo.readthedocs.io/en/stable/api/pymongo/mongo_client.html#pymongo.mongo_client.MongoClient
        try:
            response = await self.admin.command('ping') # The ping command is cheap and doesn't require auth.
            logging.info(f"Connected to mongodb: {response.get('ok', False) == 1}")
        except Exception as e:
            logging.error(f"Error while connecting to mongodb: {e}")
            logging.warning(f"Retrying connection to mongodb...")
            await self.ensure_connection()