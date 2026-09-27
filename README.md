# Test Gap Finder

Test Gap Finder is a developer tool that analyzes Python repositories to identify meaningful gaps in existing test coverage, generate targeted pytest tests, validate them, execute them safely, and report the resulting coverage improvement.

Built for the IBM Bob hackathon by:

- Dylan Glynn
- Stephen McNeil
- Ben Chadwick

## Overview

Writing tests is often reactive. Developers may have a test suite that passes while important branches, exception paths, boundary cases, and edge cases remain untested.

Test Gap Finder analyzes both source code and existing tests to answer:

- Which functions have incomplete test coverage?
- Which branches are not represented in the current tests?
- Which exception paths are missing?
- Which edge cases should be tested?
- What tests could be generated to close those gaps?
- Do the generated tests actually run successfully?
- How much does coverage improve after adding them?

For trusted local repositories, Test Gap Finder can validate and execute generated tests.

For external GitHub repositories, the application performs static analysis only and does not execute untrusted repository code.

---

## Key Features

### Repository Analysis

Test Gap Finder scans Python repositories and discovers:

- Python source files
- Test files
- Functions
- Class methods
- Async functions and methods
- Function arguments
- Branch conditions
- Raised exceptions
- Function calls
- Existing test relationships

### Test Gap Detection

The analyzer compares application code with the existing test suite and detects:

- Untested functions
- Missing branches
- Missing exception paths
- Boundary cases
- Empty input cases
- `None` input cases
- State/value-specific cases
- Dependency failure cases
- Timeout/retry-related cases

Each gap includes a confidence level:

- `high` / definitely
- `medium` / probably
- `low` / uncertain

### AI-Assisted Test Planning

Test Gap Finder can use Google Gemini to produce structured test plans from the detected gaps.

If Gemini is unavailable, not configured, or fails, the application automatically falls back to a deterministic planner.

This means the core application remains usable without an AI API key.

### Test Generation

The generated test plans are converted into pytest test cases targeted at the detected gaps.

Generated tests are validated before they are allowed to execute.

### Validation and Execution

For trusted local repositories, generated tests are:

1. Generated
2. Validated
3. Collected by pytest
4. Executed
5. Compared against the existing test suite

Test execution also includes a timeout to prevent a test run from hanging indefinitely.

### Coverage Reporting

The application measures coverage before and after generated tests are included.

It reports:

- Coverage before
- Coverage after
- Percentage-point improvement
- File-level coverage details
- Missing lines

### Potential Bug Detection

If a generated test is valid and successfully collected but fails against the target implementation, Test Gap Finder can surface it as a potential bug finding rather than simply treating it as an invalid generated test.

### GitHub Repository Analysis

Public GitHub repository URLs are supported.

External repositories are cloned temporarily and analyzed using static analysis.

For safety, external GitHub repositories are not:

- Imported
- Collected with pytest
- Executed
- Run with generated tests

The frontend clearly displays these analyses as:

> Static analysis only

### Analysis History

Previous analyses are stored using SQLite and can be:

- Viewed
- Searched
- Renamed
- Reopened
- Deleted

---

## Example Result

Using the included `sample_repo`, Test Gap Finder detects gaps in:

- `calculate_discount`
- `apply_coupon`
- `checkout`

The demonstrated pipeline produces:

- 4 existing tests
- 5 generated tests
- 9 passing tests
- 0 failed tests
- 65% coverage before
- 92% coverage after
- +27 percentage points

---

## Architecture

    Repository
        |
        v
    Repository Scanner
        |
        v
    Python AST Extraction
        |
        +----------------------+
        |                      |
        v                      v
    Source Analysis       Test Analysis
        |                      |
        +----------+-----------+
                   |
                   v
            Gap Detection
                   |
                   v
            Edge Case Detection
                   |
                   v
              Test Planner
              /         \
         Gemini      Deterministic
              \         /
                   v
            Test Generation
                   |
                   v
              Validation
                   |
                   v
         Safety / Execution Policy
              /              \
          Local             GitHub
           |                  |
           v                  v
     Execute Tests       Static Only
           |
           v
     Coverage Comparison
           |
           v
     FastAPI Backend
           |
           v
     Angular Frontend

---

## Project Structure

    test-gap-finder/
    |
    ├── analyzer/
    │   ├── code_analysis/
    │   ├── gap_detection/
    │   ├── runner/
    │   ├── security/
    │   └── test_generation/
    |
    ├── backend/
    │   ├── app/
    │   │   ├── api/
    │   │   ├── models/
    │   │   ├── services/
    │   │   └── utils/
    │   └── requirements.txt
    |
    ├── frontend/
    │   └── src/
    |
    ├── sample_repo/
    │   ├── src/
    │   └── tests/
    |
    ├── bob_sessions/
    ├── docs/
    ├── .env.example
    ├── .gitignore
    └── README.md

See the README inside each folder for more detail.

---

# Running Locally

## Prerequisites

You will need:

- Python 3.11+ recommended
- Node.js LTS
- npm
- Git

Google Gemini is optional.

---

## 1. Clone the Repository

    git clone https://github.com/ItzSteve04/test-gap-finder.git
    cd test-gap-finder

---

## 2. Create a Python Virtual Environment

From the repository root:

    python -m venv .venv

Activate it in PowerShell:

    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
    .\.venv\Scripts\Activate.ps1

Upgrade pip:

    python -m pip install --upgrade pip

Install backend dependencies:

    pip install -r backend\requirements.txt

---

# Gemini API Setup

Gemini is optional.

Without Gemini, Test Gap Finder automatically uses its deterministic planning fallback.

## 1. Create an Environment File

From the repository root:

    Copy-Item .env.example .env

Open it:

    notepad .env

Add your Gemini API key:

    GEMINI_API_KEY=your_gemini_api_key_here

If your environment file includes a Gemini model setting, keep it configured to a Gemini model available to your account.

Example:

    GEMINI_MODEL=your_available_gemini_model

## Important

Never commit your real API key.

The `.env` file should remain ignored by Git.

Only commit `.env.example` containing placeholder values.

Before pushing, check:

    git status

Your `.env` file should not appear as a tracked file.

---

## 3. Start the Backend

From the repository root with the virtual environment activated:

    python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

The API will be available at:

    http://127.0.0.1:8000

FastAPI Swagger documentation:

    http://127.0.0.1:8000/docs

Health check:

    http://127.0.0.1:8000/health

---

## 4. Install the Frontend

Open a second PowerShell terminal:

    cd frontend
    npm.cmd install

If normal `npm` works on your machine, this is equivalent:

    npm install

---

## 5. Start the Frontend

    npm.cmd start

If required, you can also use:

    npx.cmd ng serve

Open:

    http://localhost:4200

Keep the backend running at the same time.

---

# Running an Analysis

## Local Repository

Enter a trusted local repository path into the application.

For the included demo repository:

    sample_repo

Local repositories use:

    execution_mode = trusted_local

Generated tests may be validated and executed.

---

## GitHub Repository

You can also enter a public GitHub URL, for example:

    https://github.com/pallets/itsdangerous

GitHub repositories use:

    execution_mode = static_only

The repository is analyzed statically, but its code is not executed.

---

# API

Main endpoints include:

    GET    /health
    POST   /analyze

    GET    /history
    GET    /history/{entry_id}
    PATCH  /history/{entry_id}
    DELETE /history/{entry_id}

Interactive API documentation is available at:

    http://127.0.0.1:8000/docs

---

# Safety Model

Test Gap Finder distinguishes between trusted local code and externally cloned code.

## Trusted Local Repository

A local repository may:

- Be analyzed
- Have generated tests validated
- Have tests executed
- Have coverage measured

## External GitHub Repository

An externally cloned repository may:

- Be downloaded temporarily
- Be read
- Be parsed with Python AST
- Be analyzed for test gaps
- Receive generated test suggestions

It is not:

- Imported
- Executed
- Collected through pytest
- Run with generated tests

Temporary GitHub clones are automatically removed after analysis.

---

# IBM Bob

IBM Bob was used by the team throughout the hackathon development process.

Bob assisted with activities including:

- Repository architecture
- Backend development
- Static analysis features
- Test-gap logic
- Debugging
- Test generation
- Execution safety
- Refactoring
- Frontend/backend integration
- Validation
- Documentation

IBM Bob is a development tool used to help build Test Gap Finder.

It is separate from the optional Gemini integration used by the application at runtime for structured test planning.

IBM Bob task-session-summary evidence is stored under:

    bob_sessions/

---

# Technology

## Backend

- Python
- FastAPI
- Pydantic
- Python AST
- pytest
- pytest-cov
- SQLite

## Frontend

- Angular
- TypeScript
- Angular Material

## AI

- IBM Bob — development assistance
- Google Gemini — optional runtime test-plan generation
- Deterministic planner — automatic fallback

## Development

- Git
- GitHub

---

# Security

Do not commit:

- `.env`
- API keys
- Passwords
- Tokens
- IBM Cloud credentials
- Gemini credentials

Use environment variables for secrets.

Before making the repository public, review:

    git status
    git log

and verify that no credentials have ever been committed.

---

# Team

**Dylan Glynn**  
**Stephen McNeil**  
**Ben Chadwick**

Built for the IBM Bob Hackathon.