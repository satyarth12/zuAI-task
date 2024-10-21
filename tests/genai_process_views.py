import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import BackgroundTasks, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from src.genai_process.views import PDFGenAIProcessView, TextGenAIProcessView
from src.sample_paper.schema import SamplePaper


@pytest.fixture
def mock_gemini_handler():
    return MagicMock()


@pytest.fixture
def mock_mongo_repo():
    return AsyncMock()


@pytest.fixture
def mock_cache():
    return AsyncMock()


@pytest.fixture
def sample_paper():
    return SamplePaper(
        title="Sample Paper Title",
        type="previous_year",
        time=180,
        marks=100,
        params={"board": "CBSE", "grade": 10, "subject": "Maths"},
        tags=["algebra", "geometry"],
        chapters=["Quadratic Equations", "Triangles"],
        sections=[
            {
                "marks_per_question": 5,
                "type": "default",
                "questions": [
                    {
                        "question": "Solve the quadratic equation: x^2 + 5x + 6 = 0",
                        "answer": "The solutions are x = -2 and x = -3",
                        "type": "short",
                        "question_slug": "solve-quadratic-equation",
                        "reference_id": "QE001",
                        "hint": "Use the quadratic formula or factorization method",
                        "params": {},
                    },
                    {
                        "question": "In a right-angled triangle, if one angle is 30°, what is the other acute angle?",
                        "answer": "60°",
                        "type": "short",
                        "question_slug": "right-angle-triangle-angles",
                        "reference_id": "GT001",
                        "hint": "Remember that the sum of angles in a triangle is 180°",
                        "params": {},
                    },
                ],
            }
        ],
    )


class AsyncContextManagerMock:
    def __init__(self, mock_file):
        self.mock_file = mock_file

    async def __aenter__(self):
        return self.mock_file

    async def __aexit__(self, exc_type, exc, tb):
        pass


@pytest.mark.asyncio
async def test_pdf_process_success(mock_gemini_handler, mock_mongo_repo, mock_cache):
    """
    Test successful PDF processing.

    This test verifies that the PDF processing view correctly handles
    file upload, creates a task, and returns the expected response.
    """
    view = PDFGenAIProcessView(
        gemini_handler=mock_gemini_handler,
        mongo_repo=mock_mongo_repo,
        cache=mock_cache,
    )

    mock_file = AsyncMock(spec=UploadFile)
    mock_file.filename = "test.pdf"
    mock_file.read.return_value = b"mock file content"
    background_tasks = BackgroundTasks()

    mock_aiofiles_file = AsyncMock()
    mock_aiofiles_file.write = AsyncMock()

    with patch("os.path.exists", return_value=True), patch("os.makedirs"), patch(
        "aiofiles.open", return_value=AsyncContextManagerMock(mock_aiofiles_file)
    ):
        response = await view.process(mock_file, background_tasks)

    assert isinstance(response, JSONResponse)
    assert response.status_code == 202
    content = json.loads(response.body)
    assert "message" in content
    assert "task_id" in content

    mock_mongo_repo.insert_one.assert_called_once()
    mock_aiofiles_file.write.assert_called_once_with(b"mock file content")


@pytest.mark.asyncio
async def test_pdf_process_error(mock_gemini_handler, mock_mongo_repo, mock_cache):
    """
    Test PDF processing error handling.

    This test ensures that the PDF processing view correctly handles
    errors during file processing and raises the appropriate HTTP exception.
    """
    view = PDFGenAIProcessView(
        gemini_handler=mock_gemini_handler,
        mongo_repo=mock_mongo_repo,
        cache=mock_cache,
    )

    mock_file = AsyncMock(spec=UploadFile)
    mock_file.filename = "test.pdf"
    mock_file.read.side_effect = Exception("Test error")
    background_tasks = BackgroundTasks()

    with pytest.raises(HTTPException) as exc_info:
        await view.process(mock_file, background_tasks)

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Internal server error"


@pytest.mark.asyncio
async def test_text_process_success(mock_gemini_handler, mock_mongo_repo, mock_cache):
    """
    Test successful text processing.

    This test verifies that the text processing view correctly handles
    text input, creates a task, and returns the expected response.
    """
    view = TextGenAIProcessView(
        gemini_handler=mock_gemini_handler,
        mongo_repo=mock_mongo_repo,
        cache=mock_cache,
    )

    background_tasks = BackgroundTasks()
    response = await view.process("Sample text input", background_tasks)

    assert isinstance(response, JSONResponse)
    assert response.status_code == 202
    content = json.loads(response.body)
    assert "message" in content
    assert "task_id" in content

    mock_mongo_repo.insert_one.assert_called_once()


@pytest.mark.asyncio
async def test_text_process_error(mock_gemini_handler, mock_mongo_repo, mock_cache):
    """
    Test text processing error handling.

    This test ensures that the text processing view correctly handles
    errors during text processing and raises the appropriate HTTP exception.
    """
    view = TextGenAIProcessView(
        gemini_handler=mock_gemini_handler,
        mongo_repo=mock_mongo_repo,
        cache=mock_cache,
    )

    background_tasks = BackgroundTasks()
    mock_mongo_repo.insert_one.side_effect = Exception("Database error")

    with pytest.raises(HTTPException) as exc_info:
        await view.process("Sample text input", background_tasks)

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Internal server error"


@pytest.mark.asyncio
async def test_get_task_status_success(
    mock_gemini_handler, mock_mongo_repo, mock_cache
):
    """
    Test successful retrieval of task status.

    This test verifies that the get_task_status method correctly retrieves
    and returns the status of an existing task.
    """
    view = PDFGenAIProcessView(
        gemini_handler=mock_gemini_handler,
        mongo_repo=mock_mongo_repo,
        cache=mock_cache,
    )

    mock_mongo_repo.find_one.return_value = {
        "task_id": "test_task_id",
        "task_type": "pdf",
        "status": "completed",
        "error": None,
        "sample_paper_id": "sample_123",
    }

    response = await view.get_task_status("test_task_id")

    assert isinstance(response, JSONResponse)
    assert response.status_code == 200
    content = json.loads(response.body)
    assert content["task_id"] == "test_task_id"
    assert content["status"] == "completed"


@pytest.mark.asyncio
async def test_get_task_status_not_found(
    mock_gemini_handler, mock_mongo_repo, mock_cache
):
    """
    Test task status retrieval for non-existent task.

    This test ensures that the get_task_status method correctly handles
    requests for non-existent tasks and returns the appropriate response.
    """
    view = PDFGenAIProcessView(
        gemini_handler=mock_gemini_handler,
        mongo_repo=mock_mongo_repo,
        cache=mock_cache,
    )

    mock_mongo_repo.find_one.return_value = None

    response = await view.get_task_status("non_existent_task_id")

    assert isinstance(response, JSONResponse)
    assert response.status_code == 404
    content = json.loads(response.body)
    assert content["status"] == "not_found"


@pytest.mark.asyncio
async def test_store_sample_paper(
    mock_gemini_handler, mock_mongo_repo, mock_cache, sample_paper
):
    """
    Test storing a sample paper.

    This test verifies that the _store_sample_paper method correctly stores
    a sample paper and returns the expected sample paper ID.
    """
    view = PDFGenAIProcessView(
        gemini_handler=mock_gemini_handler,
        mongo_repo=mock_mongo_repo,
        cache=mock_cache,
    )

    mock_mongo_repo.insert_one.return_value = "sample_123"

    async def mock_create_sample_paper(*args, **kwargs):
        return JSONResponse(status_code=201, content={"id": "sample_123"})

    with patch("src.genai_process.views.CreateSamplePaperView") as mock_create_view:
        mock_create_view.return_value.create_sample_paper = mock_create_sample_paper
        sample_paper_id = await view._store_sample_paper(sample_paper)

    assert sample_paper_id == "sample_123"
    mock_create_view.assert_called_once()


@pytest.mark.asyncio
async def test_process_pdf_task(
    mock_gemini_handler, mock_mongo_repo, mock_cache, sample_paper
):
    """
    Test processing of a PDF task.

    This test ensures that the _process_task method for PDF files correctly
    processes the PDF, stores the resulting sample paper, and updates the task status.
    """
    view = PDFGenAIProcessView(
        gemini_handler=mock_gemini_handler,
        mongo_repo=mock_mongo_repo,
        cache=mock_cache,
    )

    mock_gemini_handler.process_pdf.return_value = sample_paper
    mock_mongo_repo.insert_one.return_value = "sample_123"

    mock_store_sample_paper = AsyncMock(return_value="sample_123")
    with patch("os.remove"), patch.object(
        view, "_store_sample_paper", mock_store_sample_paper
    ):
        await view._process_task("test_task_id", "test_file_path")

    mock_gemini_handler.process_pdf.assert_called_once_with("test_file_path")
    mock_store_sample_paper.assert_called_once_with(sample_paper)
    mock_mongo_repo.update_one.assert_called_once()


@pytest.mark.asyncio
async def test_process_text_task(
    mock_gemini_handler, mock_mongo_repo, mock_cache, sample_paper
):
    """
    Test processing of a text task.

    This test ensures that the _process_task method for text input correctly
    processes the text, stores the resulting sample paper, and updates the task status.
    """
    view = TextGenAIProcessView(
        gemini_handler=mock_gemini_handler,
        mongo_repo=mock_mongo_repo,
        cache=mock_cache,
    )

    mock_gemini_handler.process_text.return_value = sample_paper
    mock_mongo_repo.insert_one.return_value = "sample_123"

    mock_store_sample_paper = AsyncMock(return_value="sample_123")
    with patch.object(view, "_store_sample_paper", mock_store_sample_paper):
        await view._process_task("test_task_id", "Sample text input")

    mock_gemini_handler.process_text.assert_called_once_with("Sample text input")
    mock_store_sample_paper.assert_called_once_with(sample_paper)
    mock_mongo_repo.update_one.assert_called_once()
