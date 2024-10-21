import json
from abc import ABC
from dataclasses import dataclass, field

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

    async def _get_from_cache(self, paper_id: str) -> dict | None:
        cached_paper = await self.cache.get(self._get_cache_key(paper_id))
        return json.loads(cached_paper) if cached_paper else None

    async def _set_in_cache(
        self, paper_id: str, paper_data: dict, expiration: int = 3600
    ) -> None:
        paper_data.pop("_id")
        await self.cache.set(
            self._get_cache_key(paper_id), json.dumps(paper_data), expiration=expiration
        )

    async def _delete_from_cache(self, paper_id: str) -> None:
        await self.cache.delete(self._get_cache_key(paper_id))

    async def _get_from_db(self, paper_id: str) -> dict:
        paper_data = await self.mongo_repo.find_one(
            self.collection_name, {"_id": ObjectId(paper_id)}
        )
        if paper_data is None:
            raise HTTPException(
                status_code=404, detail=f"Sample paper with ID {paper_id} not found"
            )
        paper_data["id"] = str(paper_data["_id"])
        del paper_data["_id"]
        return paper_data

    async def _insert_to_db(self, paper_data: dict) -> str:
        inserted_id = await self.mongo_repo.insert_one(self.collection_name, paper_data)
        return inserted_id

    async def _update_in_db(self, paper_id: str, paper_update: dict) -> dict:
        update_result = await self.mongo_repo.update_one(
            self.collection_name, {"_id": ObjectId(paper_id)}, paper_update
        )
        if update_result == 0:
            raise HTTPException(status_code=400, detail="No fields were updated")
        return await self._get_from_db(paper_id)

    async def _delete_from_db(self, paper_id: str) -> None:
        delete_result = await self.mongo_repo.delete_one(
            self.collection_name, {"_id": ObjectId(paper_id)}
        )
        if delete_result == 0:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to delete the sample paper with ID {paper_id}",
            )


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
    View class for retrieving a sample paper.

    This class handles the retrieval of a sample paper from the cache or database.

    Methods:
        get_sample_paper(paper_id: str) -> JSONResponse: Retrieves a sample paper by ID.
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


@dataclass
class UpdateSamplePaperView(_BaseSamplePaperView):
    """
    View class for updating a sample paper.

    This class handles the update of an existing sample paper in the database and cache.

    Methods:
        update_sample_paper(paper_id: str, paper_update: dict) -> JSONResponse: Updates a sample paper.
    """

    async def update_sample_paper(
        self, paper_id: str, paper_update: dict
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
