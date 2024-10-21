import json
from abc import ABC
from dataclasses import dataclass, field
from typing import Any, Dict

from bson import ObjectId
from fastapi import HTTPException
from fastapi.responses import JSONResponse

from server import LOGGER, server_settings
from src.sample_paper.schema import SamplePaper
from src.shared_resource.cache import RedisCacheRepository
from src.shared_resource.db import AsyncMongoRepository


@dataclass
class _BaseSamplePaperView(ABC):
    """
    Base class for sample paper views providing common functionality.

    This abstract base class contains shared methods for interacting with the database
    and cache for sample paper operations.

    Attributes:
        mongo_repo (AsyncMongoRepository): Repository for MongoDB operations.
        cache (RedisCacheRepository): Repository for Redis cache operations.
        collection_name (str): Name of the MongoDB collection for sample papers.
    """

    mongo_repo: AsyncMongoRepository
    cache: RedisCacheRepository
    collection_name: str = field(
        default=server_settings.MONGODB_SAMPLE_PAPERS_COLLECTION
    )

    def _get_cache_key(self, paper_id: str) -> str:
        return f"{self.collection_name}:{paper_id}"

    async def _get_from_cache(self, paper_id: str) -> Dict[str, Any] | None:
        cached_paper = await self.cache.get(self._get_cache_key(paper_id))
        return json.loads(cached_paper) if cached_paper else None

    async def _set_in_cache(
        self, paper_id: str, paper_data: Dict[str, Any], expiration: int = 3600
    ) -> None:
        paper_data = paper_data.copy()
        paper_data.pop("_id", None)
        if "id" not in paper_data:
            paper_data["id"] = paper_id
        await self.cache.set(
            self._get_cache_key(paper_id), json.dumps(paper_data), expiration=expiration
        )

    async def _delete_from_cache(self, paper_id: str) -> None:
        await self.cache.delete(self._get_cache_key(paper_id))

    async def _get_from_db(self, paper_id: str) -> Dict[str, Any]:
        paper_data = await self.mongo_repo.find_one(
            self.collection_name, {"_id": ObjectId(paper_id)}
        )
        if paper_data is None:
            raise HTTPException(
                status_code=404, detail=f"Sample paper with ID {paper_id} not found"
            )
        paper_data["id"] = str(paper_data.pop("_id"))
        return paper_data

    async def _insert_to_db(self, paper_data: Dict[str, Any]) -> str:
        inserted_id = await self.mongo_repo.insert_one(self.collection_name, paper_data)
        return inserted_id

    async def _update_in_db(
        self, paper_id: str, paper_update: Dict[str, Any]
    ) -> Dict[str, Any]:
        update_result = await self.mongo_repo.update_one(
            self.collection_name, {"_id": ObjectId(paper_id)}, paper_update
        )
        if update_result == 0:
            raise HTTPException(status_code=400, detail="No fields were updated")
        updated_paper = await self._get_from_db(paper_id)
        return updated_paper

    async def _delete_from_db(self, paper_id: str) -> None:
        delete_result = await self.mongo_repo.delete_one(
            self.collection_name, {"_id": ObjectId(paper_id)}
        )
        if delete_result == 0:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to delete the sample paper with ID {paper_id}",
            )

    async def _search_papers(
        self, search_query: Dict[str, Any], limit: int = 10, skip: int = 0
    ) -> Dict[str, Any]:
        """
        Base method for searching sample papers.

        Args:
            search_query (Dict[str, Any]): The search query to be used.
            limit (int): The maximum number of results to return.
            skip (int): The number of results to skip (for pagination).

        Returns:
            Dict[str, Any]: A dictionary containing search results and metadata.

        Raises:
            HTTPException: If there's an error during the search process.
        """
        results = await self.mongo_repo.text_search(
            self.collection_name,
            search_query,
            limit=limit,
            skip=skip,
            sort=[("_id", -1)],
        )

        formatted_results = []
        for result in results:
            result["id"] = str(result.pop("_id"))
            formatted_results.append(result)

        total_count = await self.mongo_repo.count_documents(
            self.collection_name, search_query
        )

        return {
            "results": formatted_results,
            "total_count": total_count,
            "limit": limit,
            "skip": skip,
        }


@dataclass
class CreateSamplePaperView(_BaseSamplePaperView):
    """
    View class for creating a new sample paper.

    This class handles the creation of a new sample paper, storing it in the database
    and cache.

    Methods:
        create_sample_paper(paper: SamplePaper) -> JSONResponse: Creates a new sample paper.
    """

    async def create_sample_paper(self, paper: SamplePaper) -> JSONResponse:
        """
        Create a new sample paper.

        Args:
            paper (SamplePaper): The sample paper data to be created.

        Returns:
            JSONResponse: A response containing the created paper's ID and a success message.

        Raises:
            HTTPException: If there's an error during the creation process.
        """
        try:
            paper_dict = paper.model_dump()
            inserted_id = await self._insert_to_db(paper_dict)
            paper_dict["id"] = inserted_id
            await self._set_in_cache(inserted_id, paper_dict)

            LOGGER.info(f"Created sample paper with ID: {inserted_id}")
            return JSONResponse(
                status_code=201,
                content={
                    "message": "Sample paper created successfully",
                    "id": inserted_id,
                },
            )
        except Exception as e:
            LOGGER.error(f"Error creating sample paper: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")


@dataclass
class GetSamplePaperView(_BaseSamplePaperView):
    """
    View class for retrieving and searching sample papers.

    This class extends _BaseSamplePaperView and provides methods for fetching
    individual sample papers and performing searches across the sample paper collection.

    Attributes:
        Inherits all attributes from _BaseSamplePaperView.

    Methods:
        get_sample_paper(paper_id: str) -> JSONResponse:
            Retrieves a single sample paper by its ID.

        search_sample_papers(query: str, limit: int = 10, skip: int = 0) -> JSONResponse:
            Searches for sample papers based on a query string.

    The class utilizes both database and cache operations to optimize performance
    and reduce database load where possible.
    """

    async def get_sample_paper(self, paper_id: str) -> JSONResponse:
        """
        Retrieve a sample paper by its ID.

        Args:
            paper_id (str): The ID of the sample paper to retrieve.

        Returns:
            JSONResponse: A response containing the retrieved sample paper data.

        Raises:
            HTTPException: If the paper is not found or there's an error during retrieval.
        """
        try:
            cached_paper = await self._get_from_cache(paper_id)
            if cached_paper:
                return JSONResponse(status_code=200, content=cached_paper)

            paper_data = await self._get_from_db(paper_id)
            await self._set_in_cache(paper_id, paper_data)

            return JSONResponse(status_code=200, content=paper_data)
        except HTTPException as e:
            raise e
        except Exception as e:
            LOGGER.error(f"Error retrieving sample paper: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")

    async def search_sample_papers(
        self, query: str, limit: int = 10, skip: int = 0
    ) -> JSONResponse:
        """
        Search for sample papers based on a query string.

        Args:
            query (str): The search query for both question and answer fields.
            limit (int): The maximum number of results to return (default: 10).
            skip (int): The number of results to skip (for pagination) (default: 0).

        Returns:
            JSONResponse: A response containing the search results.

        Raises:
            HTTPException: If there's an error during the search process.
        """
        try:
            search_query = {
                "$or": [
                    {"sections.questions.question": {"$regex": query, "$options": "i"}},
                    {"sections.questions.answer": {"$regex": query, "$options": "i"}},
                ]
            }

            search_results = await self._search_papers(search_query, limit, skip)

            LOGGER.info(f"Performed search with query: {query}")
            return JSONResponse(status_code=200, content=search_results)
        except Exception as e:
            LOGGER.error(f"Error in search_sample_papers: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")


@dataclass
class UpdateSamplePaperView(_BaseSamplePaperView):
    """
    View class for updating a sample paper.

    This class handles the update of an existing sample paper in the database and cache.

    Methods:
        update_sample_paper(paper_id: str, paper_update: dict) -> JSONResponse: Updates a sample paper.
    """

    async def update_sample_paper(
        self, paper_id: str, paper_update: Dict[str, Any]
    ) -> JSONResponse:
        """
        Update a sample paper.

        Args:
            paper_id (str): The ID of the sample paper to update.
            paper_update (dict): The update data for the sample paper.

        Returns:
            JSONResponse: A response containing the updated paper data and a success message.

        Raises:
            HTTPException: If the paper is not found or there's an error during the update process.
        """
        try:
            updated_paper = await self._update_in_db(paper_id, paper_update)
            await self._set_in_cache(paper_id, updated_paper)

            LOGGER.info(f"Updated sample paper with ID: {paper_id}")
            return JSONResponse(
                status_code=200,
                content={
                    "message": "Sample paper updated successfully",
                    "paper": updated_paper,
                },
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            LOGGER.error(f"Error updating sample paper: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")


@dataclass
class DeleteSamplePaperView(_BaseSamplePaperView):
    """
    View class for deleting a sample paper.

    This class handles the deletion of a sample paper from the database and cache.

    Methods:
        delete_sample_paper(paper_id: str) -> JSONResponse: Deletes a sample paper by ID.
    """

    async def delete_sample_paper(self, paper_id: str) -> JSONResponse:
        """
        Delete a sample paper by its ID.

        Args:
            paper_id (str): The ID of the sample paper to delete.

        Returns:
            JSONResponse: A response containing a success message.

        Raises:
            HTTPException: If the paper is not found or there's an error during the deletion process.
        """
        try:
            await self._get_from_db(paper_id)  # Check if paper exists
            await self._delete_from_db(paper_id)
            await self._delete_from_cache(paper_id)

            LOGGER.info(f"Deleted sample paper with ID: {paper_id}")
            return JSONResponse(
                status_code=200,
                content={"message": "Sample paper deleted successfully"},
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            LOGGER.error(f"Error deleting sample paper: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")
