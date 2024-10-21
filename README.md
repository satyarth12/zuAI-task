# ZuAI Backend Engineer Evaluation Task
This task focuses on building a robust and efficient API for managing and processing sample papers, with a specific emphasis on integrating Gemini for PDF and text extraction.

## Setup and Installation

1. Ensure you have Python 3.11+ and [Poetry](https://python-poetry.org/) installed on your system.

2. Clone the repository:
   ```
   git clone https://github.com/satyarth12/zuAI-task.git
   cd zuAI-task
   ```

3. Install dependencies using Poetry:
   ```
   poetry install
   ```

4. Activate the virtual environment:
   ```
   poetry shell
   ```

## Project Structure

The project is organized into the following directories:

### Server Directory

The `server` directory contains the main application logic and configuration files.

- `__init__.py`: Initializes the server package.
- `api_router.py`: Contains the custom `APIRouter` class for handling API routes.
- `main.py`: The entry point for the FastAPI application.
- `settings.py`: Configuration settings for the server, including environment variables and logging.

### Source Directory

The `src` directory contains the core modules for handling sample papers and GenAI processes.

- `genai_process/`: Handles the integration with Gemini AI for processing PDFs and text.
  - `handlers.py`: Contains the `GeminiHandler` class for interacting with the Gemini API.
  - `routes.py`: Defines the API routes for GenAI processes.
  - `views.py`: Contains view classes for processing PDF and text inputs.

- `sample_paper/`: Manages the creation, retrieval, updating, and deletion of sample papers.
  - `routes.py`: Defines the API routes for sample paper operations.
  - `schema.py`: Contains Pydantic models for sample paper data validation.
  - `views.py`: Contains view classes for handling sample paper operations.

- `shared_resource/`: Provides shared resources like database and cache utilities.
  - `cache.py`: Contains the `RedisCacheRepository` class for interacting with Redis.
  - `db.py`: Contains the `AsyncMongoRepository` class for MongoDB operations and `MongoIndexManager` for index management.


## Environment Setup

### Gemini Integration

This API includes integration with Google's Gemini AI model for enhanced functionality. Ensure you have a valid Gemini API key set in your environment variables.

1. Create a `.env` file in the root directory of the project.

2. Add the following environment variables to the `.env` file:
   ```
   GEMINI_API_KEY="string"

   MONGODB_CONNECTION_STRING="string"
   MONGODB_DATABASE="string"
   MONGODB_SAMPLE_PAPERS_COLLECTION="string"
   MONGODB_GENAI_TASKS_COLLECTION="string"

   REDIS_HOST="string"
   REDIS_PORT="string"
   REDIS_PASSWORD="string"
   ```

   Adjust the values according to your setup.

## Running Tests

To run the unit tests, use the following command:

```
python -m pytest  --cov=. tests/sample_paper_views.py
```
```
python -m pytest  --cov=. tests/genai_process_views.py
```

## Running the Server
You can run the server using the following command:
```
python -m server.main
```

## API Endpoints
After running the server, the API will be available at `http://localhost:8000`. <br>
For detailed API documentation, visit `http://localhost:8000/docs`

### - Sample Paper Endpoints
   1. Create a Sample Paper:
      - POST `/sample-papers/`
      - Body: JSON object representing the sample paper

   2. Get a Sample Paper:
      - GET `/sample-papers/{paper_id}`

   3. Update a Sample Paper:
      - PUT `/sample-papers/{paper_id}`
      - Body: JSON object with fields to update

   4. Delete a Sample Paper:
      - DELETE `/sample-papers/{paper_id}`

   5. Search Sample Papers:
      - GET `/sample-papers/ft/search?query={search_query}&limit={limit}&skip={skip}`

### - GenAI Process Endpoints
   1. Extract from PDF:
      - POST `/extract/pdf`
      - Body: Form data with 'file' field containing the PDF file
      - For testing, you can use the `sample_paper.pdf` file in the `test_data` folder.

   2. Extract from Text:
      - POST `/extract/text`
      - Body: Form data with 'text' field containing the text to process

   3. Get Task Status:
      - GET `/tasks/{task_id}`


## Rate Limiting
The API implements rate limiting to prevent abuse and ensure fair usage. The rate limits are as follows:

### - Sample Paper Endpoints
   - All Sample Paper endpoints are limited to 10 requests per minute per client.

### - GenAI Process Endpoints
   - PDF and Text extraction endpoints: 5 requests per minute per client
   - Task status endpoint: 20 requests per minute per client


## Server Logs
The server logs are stored in `server.log` file.


## Indexing
Indexing is created while starting the server.
- The sample paper collection is indexed for full-text search on the question and answer fields.
- Indexing source: `src/shared_resource/db.py` : `MongoIndexManager` class.