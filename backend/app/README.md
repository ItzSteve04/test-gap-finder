# Backend Application

This directory contains the FastAPI application layer for Test Gap Finder.

The core repository-analysis logic lives in the top-level `analyzer` package, while this directory is responsible for exposing that functionality through the API.

---

## Structure

    app/
    ├── api/
    ├── models/
    ├── services/
    ├── utils/
    └── main.py

---

## `main.py`

The FastAPI application entry point.

Responsibilities include:

- Creating the FastAPI app
- Loading environment configuration
- Configuring CORS
- Initializing history storage
- Registering API routers

The file is intentionally kept small.

---

## `api/`

Contains HTTP route definitions.

### `routes.py`

Handles application routes such as:

    GET /health
    POST /analyze

### `history_routes.py`

Handles analysis history:

    GET /history
    GET /history/{entry_id}
    PATCH /history/{entry_id}
    DELETE /history/{entry_id}

---

## `models/`

Contains API and storage-related models.

Examples include:

- Analysis request models
- History rename models
- SQLite history storage

---

## `services/`

Contains application orchestration logic.

The analysis service coordinates the main pipeline:

    Repository Input
        |
        v
    Repository Resolution
        |
        v
    Analysis
        |
        v
    Test Planning
        |
        v
    Test Generation
        |
        v
    Validation / Execution Policy
        |
        v
    Test Results
        |
        v
    API Response

Keeping this orchestration in a service prevents the route layer from containing the entire analysis implementation.

---

## `utils/`

Contains backend helper functionality such as project/repository path handling.

---

## Development

Start the application from the repository root:

    python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

Swagger UI:

    http://127.0.0.1:8000/docs