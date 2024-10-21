import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import uuid4

import aiofiles
from fastapi import BackgroundTasks, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from server import LOGGER, server_settings
from src.genai_process.handlers import GeminiHandler
from src.sample_paper.schema import SamplePaper
from src.sample_paper.views import CreateSamplePaperView
from src.shared_resource.cache import RedisCacheRepository
from src.shared_resource.db import AsyncMongoRepository


@dataclass
class BaseGenAIProcessView(ABC):
    """
    Abstract base class for Gemini AI process views.

    This class provides common functionality for processing tasks,
    managing task statuses, and storing sample papers.

    Attributes:
        gemini_handler (GeminiHandler): Handler for Gemini AI operations.
        mongo_repo (AsyncMongoRepository): Repository for MongoDB operations.
        cache (RedisCacheRepository): Repository for Redis cache operations.
        collection_name (str): Name of the MongoDB collection for storing tasks.
    """

    gemini_handler: GeminiHandler
    mongo_repo: AsyncMongoRepository
    cache: RedisCacheRepository
    collection_name: str = field(default=server_settings.MONGODB_GENAI_TASKS_COLLECTION)

    @abstractmethod
    async def process(
        self, content: Any, background_tasks: BackgroundTasks
    ) -> JSONResponse:
        pass

    @abstractmethod
    async def _process_task(self, task_id: str, content: Any):
        pass

    async def _create_task_status(
        self, task_id: str, task_type: Literal["pdf", "text"]
    ) -> None:
        await self.mongo_repo.insert_one(
            self.collection_name,
            {
                "task_id": task_id,
                "task_type": task_type,
                "status": "submitted",
                "error": None,
                "sample_paper_id": None,
            },
        )

    async def _update_task_status(
        self,
        task_id: str,
        status: str,
        sample_paper_id: str = None,
        error: str = None,
    ) -> None:
        update_data = {"status": status}
        if sample_paper_id:
            update_data["sample_paper_id"] = sample_paper_id
        if error:
            update_data["error"] = error

        await self.mongo_repo.update_one(
            self.collection_name, {"task_id": task_id}, update_data
        )

    async def get_task_status(self, task_id: str) -> JSONResponse:
        task_data = await self.mongo_repo.find_one(
            self.collection_name, {"task_id": task_id}
        )
        if task_data:
            return JSONResponse(
                status_code=200,
                content={
                    "task_id": task_data["task_id"],
                    "task_type": task_data["task_type"],
                    "status": task_data["status"],
                    "error": task_data["error"],
                    "sample_paper_id": task_data["sample_paper_id"],
                },
            )

        return JSONResponse(
            status_code=404,
            content={"status": "not_found", "message": "Task not found"},
        )

    async def _store_sample_paper(self, sample_paper: SamplePaper) -> str:
        create_view = CreateSamplePaperView(self.mongo_repo, self.cache)
        response = await create_view.create_sample_paper(sample_paper)
        return json.loads(response.body)["id"]


@dataclass
class PDFGenAIProcessView(BaseGenAIProcessView):
    """
    View for processing PDF files using Gemini.

    This class handles the upload and processing of PDF files,
    creating tasks, and managing their statuses.

    Inherits from BaseGenAIProcessView.
    """

    async def process(
        self, file: UploadFile, background_tasks: BackgroundTasks
    ) -> JSONResponse:
        try:
            if not os.path.exists(server_settings.UPLOAD_DIR):
                os.makedirs(server_settings.UPLOAD_DIR)

            task_id = str(uuid4())
            await self._create_task_status(task_id, "pdf")

            file_path = os.path.join(
                server_settings.UPLOAD_DIR, f"{task_id}_{file.filename}"
            )

            async with aiofiles.open(file_path, "wb") as out_file:
                content = await file.read()
                await out_file.write(content)

            background_tasks.add_task(self._process_task, task_id, file_path)

            return JSONResponse(
                status_code=202,
                content={"message": "PDF processing started", "task_id": task_id},
            )
        except Exception as e:
            LOGGER.error(f"Error starting PDF processing: {str(e)}")
            await self._update_task_status(task_id, "error", error=str(e))
            raise HTTPException(status_code=500, detail="Internal server error")

    async def _process_task(self, task_id: str, file_path: str):
        try:
            result: SamplePaper = self.gemini_handler.process_pdf(file_path)
            sample_paper_id = await self._store_sample_paper(result)
            await self._update_task_status(
                task_id, "completed", sample_paper_id=sample_paper_id
            )
            LOGGER.info(f"PDF processing completed. Sample paper ID: {sample_paper_id}")
        except Exception as e:
            LOGGER.error(f"Error processing PDF task {task_id}: {str(e)}")
            await self._update_task_status(task_id, "error", error=str(e))
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)


@dataclass
class TextGenAIProcessView(BaseGenAIProcessView):
    """
    View for processing text input using Gemini.

    This class handles the submission and processing of text input,
    creating tasks, and managing their statuses.

    Inherits from BaseGenAIProcessView.
    """

    async def process(
        self, text: str, background_tasks: BackgroundTasks
    ) -> JSONResponse:
        try:
            task_id = str(uuid4())
            await self._create_task_status(task_id, "text")

            background_tasks.add_task(self._process_task, task_id, text)

            return JSONResponse(
                status_code=202,
                content={"message": "Text processing started", "task_id": task_id},
            )
        except Exception as e:
            LOGGER.error(f"Error starting text processing: {str(e)}")
            await self._update_task_status(task_id, "error", error=str(e))
            raise HTTPException(status_code=500, detail="Internal server error")

    async def _process_task(self, task_id: str, text: str):
        try:
            result: SamplePaper = self.gemini_handler.process_text(text)
            sample_paper_id = await self._store_sample_paper(result)
            await self._update_task_status(
                task_id, "completed", sample_paper_id=sample_paper_id
            )
            LOGGER.info(
                f"Text processing completed. Sample paper ID: {sample_paper_id}"
            )
        except Exception as e:
            LOGGER.error(f"Error processing text task {task_id}: {str(e)}")
            await self._update_task_status(task_id, "error", error=str(e))
