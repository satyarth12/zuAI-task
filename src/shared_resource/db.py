from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure

from server import LOGGER, server_settings


@dataclass
class AsyncMongoRepository:
    """
    A repository class for asynchronous interactions with MongoDB.

    This class provides methods to connect to a MongoDB server and perform various
    database operations asynchronously. It uses Motor, an asynchronous MongoDB driver,
    to enable non-blocking database operations.

    Attributes:
        database_name (str): The name of the MongoDB database to connect to.
        uri (str): The MongoDB connection string URI.
        max_pool_size (int): The maximum number of connections in the connection pool.
        min_pool_size (int): The minimum number of connections in the connection pool.
        _client (Optional[AsyncIOMotorClient]): The AsyncIOMotorClient instance.
        _db (Optional[AsyncIOMotorDatabase]): The AsyncIOMotorDatabase instance.

    Methods:
        connect(): Establishes a connection to the MongoDB server.
        disconnect(): Closes the connection to the MongoDB server.
        insert_one(collection, document): Inserts a single document into a collection.
        find_one(collection, query): Finds a single document in a collection.
        find_many(collection, query): Finds multiple documents in a collection.
        update_one(collection, query, update): Updates a single document in a collection.
        delete_one(collection, query): Deletes a single document from a collection.
        count_documents(collection, query): Counts documents in a collection based on a query.
    """

    database_name: str
    uri: str = field(default_factory=lambda: server_settings.MONGODB_CONNECTION_STRING)
    max_pool_size: int = field(
        default_factory=lambda: server_settings.MONGODB_MAX_POOL_SIZE
    )
    min_pool_size: int = field(
        default_factory=lambda: server_settings.MONGODB_MIN_POOL_SIZE
    )
    _client: Optional[AsyncIOMotorClient] = None
    _db: Optional[AsyncIOMotorDatabase] = None

    def connect(self):
        if self._client is None:
            try:
                self._client = AsyncIOMotorClient(
                    self.uri,
                    maxPoolSize=self.max_pool_size,
                    minPoolSize=self.min_pool_size,
                )
                self._db = self._client[self.database_name]
                LOGGER.info("Connected to MongoDB")
            except ConnectionFailure:
                LOGGER.error("Failed to connect to MongoDB")
                raise

    async def disconnect(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None
            self._db = None
            LOGGER.info("Disconnected from MongoDB")

    async def insert_one(self, collection: str, document: Dict[str, Any]) -> str:
        result = await self._db[collection].insert_one(document)
        return str(result.inserted_id)

    async def find_one(
        self, collection: str, query: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        return await self._db[collection].find_one(query)

    async def find_many(
        self, collection: str, query: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        cursor = self._db[collection].find(query)
        return await cursor.to_list(length=None)

    async def update_one(
        self, collection: str, query: Dict[str, Any], update: Dict[str, Any]
    ) -> int:
        result = await self._db[collection].update_one(query, {"$set": update})
        return result.modified_count

    async def delete_one(self, collection: str, query: Dict[str, Any]) -> int:
        result = await self._db[collection].delete_one(query)
        return result.deleted_count

    async def count_documents(self, collection: str, query: Dict[str, Any]) -> int:
        return await self._db[collection].count_documents(query)


async def get_mongo_repo():
    repo = AsyncMongoRepository(database_name=server_settings.MONGODB_DATABASE)
    repo.connect()
    return repo
