# Backend

The Test Gap Finder backend is a FastAPI application that exposes the analysis pipeline to the Angular frontend.

It coordinates repository analysis, test-gap detection, test generation, validation, execution, coverage reporting, safety controls, and analysis history.

---

## Structure

    backend/
    ├── app/
    │   ├── api/
    │   │   ├── routes.py
    │   │   └── history_routes.py
    │   │
    │   ├── models/
    │   │   ├── analyze.py
    │   │   ├── history.py
    │   │   └── history_store.py
    │   │
    │   ├── services/
    │   │   └── analysis_service.py
    │   │
    │   ├── utils/
    │   │   └── paths.py
    │   │
    │   └── main.py
    │
    └── requirements.txt

---

## Responsibilities

The backend handles:

- API requests
- Repository source resolution
- Local path validation
- GitHub repository ingestion
- Execution policy selection
- Repository analysis
- Test planning
- Test generation
- Generated-test validation
- Test execution
- Coverage reporting
- Potential bug findings
- Analysis history

---

## API Routes

### Health Check

    GET /health

Used to verify that the backend is running.

Example response:

    {
      "status": "ok"
    }

---

## Analyze Repository

    POST /analyze

Analyzes a repository.

The repository may be:

- A trusted local path
- A public GitHub repository URL

Example request:

    {
      "repository_url": "sample_repo"
    }

The response may include:

- Repository information
- Source type
- Execution mode
- Safety policy
- Python file count
- Test file count
- Detected gaps
- Test plans
- Generated tests
- Validation results
- Test results
- Coverage details
- Potential bug findings
- History metadata

---

## History API

### List History

    GET /history

Returns saved analysis history.

### Get One Entry

    GET /history/{entry_id}

Returns one stored analysis.

### Rename Entry

    PATCH /history/{entry_id}

Used to rename a history item.

### Delete Entry

    DELETE /history/{entry_id}

Deletes a stored analysis.

---

## SQLite History Storage

Analysis history is stored using SQLite.

The database is stored under:

    backend/data/

The database directory should not be committed to Git.

It is intended to be generated locally at runtime.

---

# Local Setup

## 1. Create a Virtual Environment

From the project root:

    python -m venv .venv

---

## 2. Activate the Virtual Environment

PowerShell:

    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
    .\.venv\Scripts\Activate.ps1

---

## 3. Install Dependencies

From the project root:

    pip install -r backend\requirements.txt

---

# Gemini Configuration

Google Gemini is optional.

If no Gemini key is configured, Test Gap Finder falls back to its deterministic planner.

## Create `.env`

From the repository root:

    Copy-Item .env.example .env

Open the file:

    notepad .env

Add:

    GEMINI_API_KEY=your_gemini_api_key_here

Optionally configure a Gemini model if supported by your environment:

    GEMINI_MODEL=your_available_gemini_model

Do not commit your real `.env` file.

Only `.env.example` should contain placeholder configuration.

---

# Start the Backend

From the repository root with the virtual environment activated:

    python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

The API will be available at:

    http://127.0.0.1:8000

---

## Swagger UI

FastAPI automatically provides interactive API documentation.

Open:

    http://127.0.0.1:8000/docs

This can be used to inspect and test endpoints such as:

    GET /health
    POST /analyze
    GET /history
    GET /history/{entry_id}
    PATCH /history/{entry_id}
    DELETE /history/{entry_id}

---

## Health Check

Open:

    http://127.0.0.1:8000/health

You should receive a successful health response.

---

# CORS

During local development, the backend allows requests from the Angular frontend running at:

    http://localhost:4200

The frontend and backend should both be running at the same time.

---

# Execution Safety

The backend determines execution permissions based on repository source.

## Local Repository

Trusted local repositories may be:

- Parsed
- Validated
- Collected with pytest
- Executed
- Measured with coverage

The execution mode is:

    trusted_local

---

## GitHub Repository

External GitHub repositories use:

    static_only

The backend can:

- Clone the repository temporarily
- Discover Python files
- Parse Python code
- Detect test gaps
- Generate test suggestions

It does not:

- Import target repository code
- Collect its tests with pytest
- Execute its existing tests
- Execute generated tests

This prevents arbitrary code from external repositories from being run automatically.

---

# Temporary GitHub Repositories

GitHub repositories are analyzed from temporary directories.

Once analysis finishes, the temporary clone is removed automatically.

---

# Development Notes

When changing backend code, useful checks include:

    python -m compileall backend analyzer

and running the available automated tests.

The backend is intentionally structured into API routes, services, models, and utilities to keep the FastAPI entry point small and maintainable.