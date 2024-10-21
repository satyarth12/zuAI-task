# ZuAI Backend Engineer Evaluation Task

## Sample Paper API with Gemini Integration

This project implements a Sample Paper API with Gemini integration, providing endpoints for managing and searching sample papers.

### Setup and Installation

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

### Environment Setup

#### Gemini Integration

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

### Running Tests

To run the unit tests, use the following command:

```
python -m pytest  --cov=. tests/sample_paper_views.py
```
```
python -m pytest  --cov=. tests/genai_process_views.py
```



### API Endpoints
The API will be available at `http://localhost:8000`.

#### - Sample Paper Endpoints
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

#### - GenAI Process Endpoints
   1. Extract from PDF:
      - POST `/extract/pdf`
      - Body: Form data with 'file' field containing the PDF file

   2. Extract from Text:
      - POST `/extract/text`
      - Body: Form data with 'text' field containing the text to process

   3. Get Task Status:
      - GET `/tasks/{task_id}`

For detailed API documentation, visit `http://localhost:8000/docs` after starting the server.

### Rate Limiting
The API implements rate limiting to prevent abuse and ensure fair usage. The rate limits are as follows:

#### - Sample Paper Endpoints
   - All Sample Paper endpoints are limited to 10 requests per minute per client.

#### - GenAI Process Endpoints
   - PDF and Text extraction endpoints: 5 requests per minute per client
   - Task status endpoint: 20 requests per minute per client


### Server Logs
The server logs are stored in `server.log` file.


### Indexing
Indexing is created while starting the server.
- The sample paper collection is indexed for full-text search on the question and answer fields.
- Indexing source: `src/shared_resource/db.py` : `MongoIndexManager` class.