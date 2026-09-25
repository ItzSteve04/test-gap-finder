# Backend

This folder contains the backend API for Test Gap Finder.

The backend acts as the coordinator between the frontend, repository analysis, test-gap detection, generated tests, and test execution.

The backend is being developed using Python and FastAPI.

## Main Responsibilities

The backend will be responsible for:

- receiving requests from the Angular frontend
- accepting repository information
- retrieving repository contents
- starting the analysis process
- communicating with the analysis engine
- managing test generation
- running tests
- collecting test and coverage results
- returning structured results to the frontend

## `app/`

Contains the FastAPI application and the main backend logic.

### `app/main.py`

The main entry point for the FastAPI application.

This file creates the FastAPI application and connects the different parts of the backend.

### `app/api/`

Contains API-related code.

This area is responsible for endpoints that the Angular frontend can call.

For example, analysis requests and result requests will eventually be handled through this part of the backend.

### `app/services/`

Contains backend service logic.

Services handle larger operations that should not be placed directly inside API endpoints.

Examples include coordinating repository analysis, starting test execution, or communicating with the analysis engine.

### `app/models/`

Contains data structures used by the backend.

These models can describe the structure of requests, responses, analysis results, test gaps, or other information exchanged by the application.

### `app/utils/`

Contains small reusable helper functions used by different parts of the backend.

Utilities should contain supporting functionality rather than major application logic.

## `tests/`

Contains tests for the Test Gap Finder backend itself.

These tests make sure that our own API and backend functionality behave correctly.

This is separate from the tests belonging to repositories analyzed by Test Gap Finder.

## `requirements.txt`

Contains the Python packages required to run the backend.

This allows developers to install the backend dependencies consistently.
