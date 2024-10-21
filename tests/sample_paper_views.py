import json
from unittest.mock import AsyncMock

import pytest
from bson import ObjectId
from fastapi import HTTPException
from fastapi.responses import JSONResponse

from src.sample_paper.schema import SamplePaper
from src.sample_paper.views import (
    CreateSamplePaperView,
    DeleteSamplePaperView,
    GetSamplePaperView,
    UpdateSamplePaperView,
)


@pytest.fixture
def mock_mongo_repo():
    return AsyncMock()


@pytest.fixture
def mock_cache():
    return AsyncMock()


@pytest.fixture
def sample_paper_data():
    return {
        "title": "Sample Paper Title",
        "type": "previous_year",
        "time": 180,
        "marks": 100,
        "params": {"board": "CBSE", "grade": 10, "subject": "Maths"},
        "tags": ["algebra", "geometry"],
        "chapters": ["Quadratic Equations", "Triangles"],
        "sections": [
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
    }


@pytest.fixture
def valid_object_id():
    return str(ObjectId())


@pytest.mark.asyncio
async def test_create_sample_paper_success(
    mock_mongo_repo, mock_cache, sample_paper_data, valid_object_id
):
    """
    Test successful creation of a sample paper.

    This test verifies that the create_sample_paper method correctly creates
    a new sample paper, stores it in the database and cache, and returns the expected response.
    """
    view = CreateSamplePaperView(mongo_repo=mock_mongo_repo, cache=mock_cache)
    mock_mongo_repo.insert_one.return_value = valid_object_id

    paper = SamplePaper(**sample_paper_data)
    response = await view.create_sample_paper(paper)

    assert isinstance(response, JSONResponse)
    assert response.status_code == 201
    assert json.loads(response.body) == {
        "message": "Sample paper created successfully",
        "id": valid_object_id,
    }

    mock_mongo_repo.insert_one.assert_called_once()
    mock_cache.set.assert_called_once()


@pytest.mark.asyncio
async def test_create_sample_paper_error(
    mock_mongo_repo, mock_cache, sample_paper_data
):
    """
    Test error handling during sample paper creation.

    This test ensures that the create_sample_paper method correctly handles
    errors during the creation process and raises the appropriate HTTP exception.
    """
    view = CreateSamplePaperView(mongo_repo=mock_mongo_repo, cache=mock_cache)
    mock_mongo_repo.insert_one.side_effect = Exception("Database error")

    paper = SamplePaper(**sample_paper_data)
    with pytest.raises(HTTPException) as exc_info:
        await view.create_sample_paper(paper)

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Internal server error"


@pytest.mark.asyncio
async def test_get_sample_paper_from_cache(
    mock_mongo_repo, mock_cache, valid_object_id
):
    """
    Test retrieval of a sample paper from cache.

    This test verifies that the get_sample_paper method correctly retrieves
    a sample paper from the cache when it's available.
    """
    view = GetSamplePaperView(mongo_repo=mock_mongo_repo, cache=mock_cache)
    mock_cache.get.return_value = json.dumps(
        {"id": valid_object_id, "title": "Cached Paper"}
    )

    response = await view.get_sample_paper(valid_object_id)

    assert isinstance(response, JSONResponse)
    assert response.status_code == 200
    assert json.loads(response.body) == {
        "id": valid_object_id,
        "title": "Cached Paper",
    }

    mock_cache.get.assert_called_once()
    mock_mongo_repo.find_one.assert_not_called()


@pytest.mark.asyncio
async def test_get_sample_paper_from_db(mock_mongo_repo, mock_cache, valid_object_id):
    """
    Test retrieval of a sample paper from the database.

    This test ensures that the get_sample_paper method correctly retrieves
    a sample paper from the database when it's not found in the cache.
    """
    view = GetSamplePaperView(mongo_repo=mock_mongo_repo, cache=mock_cache)
    mock_cache.get.return_value = None
    mock_mongo_repo.find_one.return_value = {
        "_id": ObjectId(valid_object_id),
        "title": "DB Paper",
    }

    response = await view.get_sample_paper(valid_object_id)

    assert isinstance(response, JSONResponse)
    assert response.status_code == 200
    assert json.loads(response.body) == {"id": valid_object_id, "title": "DB Paper"}

    mock_cache.get.assert_called_once()
    mock_mongo_repo.find_one.assert_called_once()
    mock_cache.set.assert_called_once()


@pytest.mark.asyncio
async def test_get_sample_paper_not_found(mock_mongo_repo, mock_cache, valid_object_id):
    """
    Test error handling when a sample paper is not found.

    This test verifies that the get_sample_paper method raises the appropriate
    HTTP exception when a sample paper is not found in either the cache or the database.
    """
    view = GetSamplePaperView(mongo_repo=mock_mongo_repo, cache=mock_cache)
    mock_cache.get.return_value = None
    mock_mongo_repo.find_one.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        await view.get_sample_paper(valid_object_id)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == f"Sample paper with ID {valid_object_id} not found"


@pytest.mark.asyncio
async def test_update_sample_paper_success(
    mock_mongo_repo, mock_cache, valid_object_id
):
    """
    Test successful update of a sample paper.

    This test ensures that the update_sample_paper method correctly updates
    a sample paper in the database and cache, and returns the expected response.
    """
    view = UpdateSamplePaperView(mongo_repo=mock_mongo_repo, cache=mock_cache)
    mock_mongo_repo.update_one.return_value = 1
    mock_mongo_repo.find_one.return_value = {
        "_id": ObjectId(valid_object_id),
        "title": "Updated Paper",
    }

    response = await view.update_sample_paper(
        valid_object_id, {"title": "Updated Paper"}
    )

    assert isinstance(response, JSONResponse)
    assert response.status_code == 200
    assert json.loads(response.body) == {
        "message": "Sample paper updated successfully",
        "paper": {"id": valid_object_id, "title": "Updated Paper"},
    }

    mock_mongo_repo.update_one.assert_called_once()
    mock_mongo_repo.find_one.assert_called_once()
    mock_cache.set.assert_called_once()


@pytest.mark.asyncio
async def test_update_sample_paper_not_found(
    mock_mongo_repo, mock_cache, valid_object_id
):
    """
    Test error handling when updating a non-existent sample paper.

    This test verifies that the update_sample_paper method raises the appropriate
    HTTP exception when attempting to update a non-existent sample paper.
    """
    view = UpdateSamplePaperView(mongo_repo=mock_mongo_repo, cache=mock_cache)
    mock_mongo_repo.update_one.return_value = 0

    with pytest.raises(HTTPException) as exc_info:
        await view.update_sample_paper(valid_object_id, {"title": "Updated Paper"})

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "No fields were updated"


@pytest.mark.asyncio
async def test_delete_sample_paper_success(
    mock_mongo_repo, mock_cache, valid_object_id
):
    """
    Test successful deletion of a sample paper.

    This test ensures that the delete_sample_paper method correctly deletes
    a sample paper from the database and cache, and returns the expected response.
    """
    view = DeleteSamplePaperView(mongo_repo=mock_mongo_repo, cache=mock_cache)
    mock_mongo_repo.find_one.return_value = {
        "_id": ObjectId(valid_object_id),
        "title": "Paper to Delete",
    }
    mock_mongo_repo.delete_one.return_value = 1

    response = await view.delete_sample_paper(valid_object_id)

    assert isinstance(response, JSONResponse)
    assert response.status_code == 200
    assert json.loads(response.body) == {"message": "Sample paper deleted successfully"}

    mock_mongo_repo.find_one.assert_called_once()
    mock_mongo_repo.delete_one.assert_called_once()
    mock_cache.delete.assert_called_once()


@pytest.mark.asyncio
async def test_delete_sample_paper_not_found(
    mock_mongo_repo, mock_cache, valid_object_id
):
    """
    Test error handling when deleting a non-existent sample paper.

    This test verifies that the delete_sample_paper method raises the appropriate
    HTTP exception when attempting to delete a non-existent sample paper.
    """
    view = DeleteSamplePaperView(mongo_repo=mock_mongo_repo, cache=mock_cache)
    mock_mongo_repo.find_one.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        await view.delete_sample_paper(valid_object_id)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == f"Sample paper with ID {valid_object_id} not found"


@pytest.mark.asyncio
async def test_delete_sample_paper_failure(
    mock_mongo_repo, mock_cache, valid_object_id
):
    """
    Test error handling when sample paper deletion fails.

    This test ensures that the delete_sample_paper method raises the appropriate
    HTTP exception when the deletion operation fails in the database.
    """
    view = DeleteSamplePaperView(mongo_repo=mock_mongo_repo, cache=mock_cache)
    mock_mongo_repo.find_one.return_value = {
        "_id": ObjectId(valid_object_id),
        "title": "Paper to Delete",
    }
    mock_mongo_repo.delete_one.return_value = 0

    with pytest.raises(HTTPException) as exc_info:
        await view.delete_sample_paper(valid_object_id)

    assert exc_info.value.status_code == 400
    assert (
        exc_info.value.detail
        == f"Failed to delete the sample paper with ID {valid_object_id}"
    )


@pytest.mark.asyncio
async def test_search_sample_papers(mock_mongo_repo, mock_cache):
    """
    Test searching for sample papers.

    This test verifies that the search_sample_papers method correctly searches
    for sample papers based on a query string and returns the expected results.
    """
    view = GetSamplePaperView(mongo_repo=mock_mongo_repo, cache=mock_cache)

    # Mock the search results
    mock_search_results = [
        {
            "_id": ObjectId(),
            "title": "Sample Paper Title",
            "type": "previous_year",
            "time": 180,
            "marks": 100,
            "params": {"board": "CBSE", "grade": 10, "subject": "Maths"},
            "tags": ["algebra", "geometry"],
            "chapters": ["Quadratic Equations", "Triangles"],
            "sections": {
                "marks_per_question": 5,
                "type": "default",
                "questions": {
                    "question": "In a right-angled triangle, if one angle is 30°, what is the other acute angle?",
                    "answer": "60°",
                    "type": "short",
                    "question_slug": "right-angle-triangle-angles",
                    "reference_id": "GT001",
                    "hint": "Remember that the sum of angles in a triangle is 180°",
                    "params": {},
                },
            },
            "matched_questions": [
                {
                    "question": "In a right-angled triangle, if one angle is 30°, what is the other acute angle?",
                    "answer": "60°",
                }
            ],
        },
        {
            "_id": ObjectId(),
            "title": "Another Sample Paper",
            "type": "previous_year",
            "time": 180,
            "marks": 100,
            "params": {"board": "CBSE", "grade": 10, "subject": "Maths"},
            "tags": ["algebra", "geometry"],
            "chapters": ["Quadratic Equations", "Triangles"],
            "sections": {
                "marks_per_question": 5,
                "type": "default",
                "questions": {
                    "question": "What is the Pythagorean theorem?",
                    "answer": "In a right-angled triangle, the square of the hypotenuse is equal to the sum of squares of the other two sides.",
                    "type": "short",
                    "question_slug": "pythagorean-theorem",
                    "reference_id": "GT002",
                    "hint": "Think about the relationship between sides in a right-angled triangle",
                    "params": {},
                },
            },
            "matched_questions": [
                {
                    "question": "What is the Pythagorean theorem?",
                    "answer": "In a right-angled triangle, the square of the hypotenuse is equal to the sum of squares of the other two sides.",
                }
            ],
        },
    ]

    expected_response = {
        "results": [
            {**result, "id": str(result["_id"])} for result in mock_search_results
        ],
        "total_count": len(mock_search_results),
        "limit": 10,
        "skip": 0,
    }

    # Remove _id from expected results
    for result in expected_response["results"]:
        result.pop("_id")

    # Set up the mock for text_search
    mock_mongo_repo.text_search.return_value = mock_search_results
    mock_mongo_repo.count_documents.return_value = len(mock_search_results)

    # Perform the search
    query = "triangle"
    limit = 10
    skip = 0
    response = await view.search_sample_papers(query, limit, skip)

    # Assert the response
    assert isinstance(response, JSONResponse)
    assert response.status_code == 200

    content = json.loads(response.body)
    assert content == expected_response

    # Verify that the correct methods were called
    expected_search_query = {
        "$or": [
            {"sections.questions.question": {"$regex": query, "$options": "i"}},
            {"sections.questions.answer": {"$regex": query, "$options": "i"}},
        ]
    }
    mock_mongo_repo.text_search.assert_called_once_with(
        view.collection_name,
        expected_search_query,
        limit=limit,
        skip=skip,
        sort=[("_id", -1)],
    )
    mock_mongo_repo.count_documents.assert_called_once_with(
        view.collection_name, expected_search_query
    )


@pytest.mark.asyncio
async def test_search_sample_papers_error(mock_mongo_repo, mock_cache):
    """
    Test error handling in search_sample_papers method.

    This test ensures that the search_sample_papers method correctly handles
    errors and raises the appropriate HTTP exception.
    """
    view = GetSamplePaperView(mongo_repo=mock_mongo_repo, cache=mock_cache)

    # Set up the mock to raise an exception
    mock_mongo_repo.text_search.side_effect = Exception("Database error")

    # Attempt to perform the search
    with pytest.raises(HTTPException) as exc_info:
        await view.search_sample_papers("query", 10, 0)

    # Assert the exception details
    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Internal server error"
