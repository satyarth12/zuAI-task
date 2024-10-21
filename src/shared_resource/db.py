from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, TEXT, IndexModel
from pymongo.errors import ConnectionFailure, OperationFailure

from server import LOGGER, server_settings


@dataclass
class MongoIndexManager:
    """
    A class to manage MongoDB index operations.

    This class provides methods to define and manage indexes for MongoDB collections.

    Methods:
        get_sample_paper_indexes(): Returns a list of IndexModel objects for the sample paper collection.
    """

    @staticmethod
    def get_sample_paper_indexes():
        """
        Get the indexes for the sample paper collection.

        Returns:
            List[IndexModel]: A list of IndexModel objects defining the indexes for the sample paper collection.
        """
        return [
            IndexModel(
                [
                    ("sections.questions.question", TEXT),
                    ("sections.questions.answer", TEXT),
                ],
                name="question_answer_text",
                weights={
                    "sections.questions.question": 10,
                    "sections.questions.answer": 10,
                },
            ),
            IndexModel([("_id", ASCENDING)], name="id_index"),
        ]


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
        find_many(collection, query, limit, skip, sort): Finds multiple documents in a collection.
        update_one(collection, query, update): Updates a single document in a collection.
        delete_one(collection, query): Deletes a single document from a collection.
        count_documents(collection, query): Counts documents in a collection based on a query.
        create_indexes(collection_name, indexes): Create indexes for a given collection.
        text_search(collection, search_query, limit, skip, sort): Performs a text search on a collection.
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
        self,
        collection: str,
        query: Dict[str, Any],
        limit: int = 0,
        skip: int = 0,
        sort: List[tuple[str, Union[int, Dict[str, Any]]]] = None,
    ) -> List[Dict[str, Any]]:
        cursor = self._db[collection].find(query)

        if skip:
            cursor = cursor.skip(skip)
        if limit:
            cursor = cursor.limit(limit)
        if sort:
            cursor = cursor.sort(sort)

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

    async def create_indexes(self, collection_name: str, indexes: list[IndexModel]):
        """
        Create indexes for a given collection.

        Args:
            collection_name (str): The name of the collection to create indexes for.
            indexes (list[IndexModel]): A list of IndexModel objects defining the indexes to create.
        """
        for index in indexes:
            try:
                await self._db[collection_name].create_indexes([index])
                LOGGER.info(
                    f"Created index '{index.document['name']}' on collection '{collection_name}'"
                )
            except OperationFailure as e:
                if e.code == 85:  # IndexOptionsConflict
                    LOGGER.warning(
                        f"Dropping existing index '{index.document['name']}' due to options conflict"
                    )
                    await self._db[collection_name].drop_index(index.document["name"])
                    await self._db[collection_name].create_indexes([index])
                    LOGGER.info(
                        f"Created index '{index.document['name']}' on collection '{collection_name}'"
                    )
                else:
                    raise

    async def text_search(
        self,
        collection_name: str,
        search_query: Dict[str, Any],
        limit: int = 10,
        skip: int = 0,
        sort: Optional[List[Tuple[str, int]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Perform a text search on the specified collection using the given search query.

        This method executes a text search on the MongoDB collection using the provided
        search query. It supports pagination through limit and skip parameters, and
        allows custom sorting of the results.

        Args:
            collection_name (str): The name of the MongoDB collection to search.
            search_query (Dict[str, Any]): The search query to be used. This should be a
                dictionary containing the search criteria.
            limit (int, optional): The maximum number of documents to return. Defaults to 10.
            skip (int, optional): The number of documents to skip before starting to return
                results. Useful for pagination. Defaults to 0.
            sort (Optional[List[Tuple[str, int]]], optional): A list of tuples specifying
                the sort order. Each tuple should contain the field name and sort direction
                (1 for ascending, -1 for descending). Defaults to None.

        Returns:
            List[Dict[str, Any]]: A list of documents matching the search criteria. Each
            document is represented as a dictionary.

        Raises:
            Exception: If there's an error during the database operation.

        Example:
            search_query = {"$text": {"$search": "python programming"}}
            sort_order = [("score", {"$meta": "textScore"}), ("date", -1)]
            results = await repo.text_search("articles", search_query, limit=5, skip=10, sort=sort_order)
        """
        pipeline = [
            {"$match": search_query},
            {"$unwind": "$sections"},
            {"$unwind": "$sections.questions"},
            {"$match": search_query},
            {
                "$group": {
                    "_id": "$_id",
                    "doc": {"$first": "$$ROOT"},
                    "matched_questions": {
                        "$push": {
                            "question": "$sections.questions.question",
                            "answer": "$sections.questions.answer",
                        }
                    },
                }
            },
            {
                "$replaceRoot": {
                    "newRoot": {
                        "$mergeObjects": [
                            "$doc",
                            {"matched_questions": "$matched_questions"},
                        ]
                    }
                }
            },
        ]

        if skip:
            pipeline.append({"$skip": skip})
        if limit:
            pipeline.append({"$limit": limit})
        if sort:
            pipeline.append({"$sort": dict(sort)})

        cursor = self._db[collection_name].aggregate(pipeline)
        return await cursor.to_list(length=None)


async def get_mongo_repo():
    repo = AsyncMongoRepository(database_name=server_settings.MONGODB_DATABASE)
    repo.connect()
    return repo


async def create_indexes():
    mongo_repo = await get_mongo_repo()
    await mongo_repo.create_indexes(
        server_settings.MONGODB_SAMPLE_PAPERS_COLLECTION,
        MongoIndexManager.get_sample_paper_indexes(),
    )
    await mongo_repo.disconnect()
