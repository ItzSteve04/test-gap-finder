# Test Gap Finder

Test Gap Finder is an AI-assisted developer tool built for the IBM Bob 2.0 Hackathon.

The goal of the project is to help developers identify important areas of a codebase that are missing tests, generate targeted tests for those gaps, run the tests, and present the results in a clear interface.

## Problem

Existing test coverage does not always mean that the important behaviour of an application is properly tested.

Developers may miss:

- edge cases
- error-handling paths
- boundary conditions
- risky business logic
- recently added functionality
- functions or classes with little or no test coverage

Finding these gaps manually can take significant time, especially in unfamiliar codebases.

## Solution

Test Gap Finder analyzes a repository's source code and existing tests to identify potentially important missing test cases.

The intended workflow is:

1. A user provides a repository.
2. The application retrieves and analyzes the repository.
3. Existing source code and tests are inspected.
4. Potential test gaps are identified.
5. IBM Bob assists with generating targeted tests.
6. The existing and generated tests are executed.
7. Results are displayed to the user, including test gaps, generated tests, failures, and coverage information.

## Project Architecture

### `frontend/`

Contains the web application used by the developer.

The frontend is being built with Angular and is responsible for displaying the interface, accepting repository information, showing analysis progress, and presenting the final results.

### `backend/`

Contains the Python/FastAPI backend.

The backend acts as the connection between the frontend, repository data, the Python analysis engine, test generation, and test execution.

### `analyzer/`

Contains the main Python code-analysis functionality.

This part of the project is responsible for inspecting source code, existing tests, coverage information, and identifying potential test gaps.

### `sample_repo/`

Contains a controlled example project used to develop, test, and demonstrate Test Gap Finder.

The sample repository will contain source code and tests so that the team can reliably demonstrate missing test cases and potential bugs.

### `bob_sessions/`

Contains evidence of how each team member used IBM Bob during the hackathon.

Each team member has their own folder for storing IBM Bob task-session-summary screenshots or other required session evidence.

### `docs/`

Contains project documentation used to explain the problem, architecture, IBM Bob usage, and final demonstration.

### `.github/workflows/`

Reserved for GitHub workflow configuration used by the project.

## Technology

The project currently uses:

- Angular
- TypeScript
- Python
- FastAPI
- pytest
- pytest-cov / coverage
- GitHub
- IBM Bob 2.0

## Hackathon Goal

The project aims to demonstrate how IBM Bob 2.0 can improve the software testing workflow by reducing the manual effort required to identify missing tests and helping developers create targeted tests for risky or untested behaviour.
