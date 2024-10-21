from fastapi import BackgroundTasks, Depends, File, Form, HTTPException, UploadFile

from server import APIRouter
from src.genai_process.handlers import GeminiHandler
from src.genai_process.views import PDFGenAIProcessView, TextGenAIProcessView
from src.shared_resource.cache import RedisCacheRepository, get_redis_cache
from src.shared_resource.db import AsyncMongoRepository, get_mongo_repo

extraction_router = APIRouter(tags=["extraction"])


async def get_pdf_genai_process_view(
    mongo_repo: AsyncMongoRepository = Depends(get_mongo_repo),
    cache: RedisCacheRepository = Depends(get_redis_cache),
) -> PDFGenAIProcessView:
    gemini_handler = GeminiHandler()
    return PDFGenAIProcessView(gemini_handler, mongo_repo, cache)


async def get_text_genai_process_view(
    mongo_repo: AsyncMongoRepository = Depends(get_mongo_repo),
    cache: RedisCacheRepository = Depends(get_redis_cache),
) -> TextGenAIProcessView:
    gemini_handler = GeminiHandler()
    return TextGenAIProcessView(gemini_handler, mongo_repo, cache)


@extraction_router.post("/extract/pdf")
async def extract_pdf(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    pdf_view: PDFGenAIProcessView = Depends(get_pdf_genai_process_view),
):
    """
    Extract information from a PDF file.

    This endpoint accepts a PDF file upload, processes it asynchronously,
    and returns a task ID for tracking the extraction progress.
    """
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    return await pdf_view.process(file, background_tasks)


@extraction_router.post("/extract/text")
async def extract_text(
    text: str = Form(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    text_view: TextGenAIProcessView = Depends(get_text_genai_process_view),
):
    """
    Extract information from text content.

    This endpoint accepts text input, processes it asynchronously,
    and returns a task ID for tracking the extraction progress.
    """
    return await text_view.process(text, background_tasks)


@extraction_router.get("/tasks/{task_id}")
async def get_task_status(
    task_id: str,
    pdf_view: PDFGenAIProcessView = Depends(get_pdf_genai_process_view),
):
    """
    Get the status of a processing task.

    This endpoint retrieves the current status of a task by its ID.
    It can be used for both PDF and text processing tasks.
    """
    return await pdf_view.get_task_status(task_id)
