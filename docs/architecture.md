# Test Gap Finder Architecture

Test Gap Finder is designed as a multi-stage repository analysis pipeline.

The main goal is to inspect Python source code and its existing tests, detect meaningful gaps, generate targeted pytest tests, validate them, and measure their impact.

---

## High-Level Flow

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
         Execution Safety Policy
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
       FastAPI API
           |
           v
     Angular Frontend

---

## Repository Scanning

The first stage discovers:

- Python source files
- Test files
- Source directories
- Test directories

The repository can be either:

- A trusted local repository
- A public GitHub repository

---

## Static Code Analysis

Python source code is analyzed using Python's Abstract Syntax Tree (`ast`).

The analyzer extracts metadata including:

- Function names
- Qualified names
- Class names
- Methods
- Async functions
- Arguments
- Branch conditions
- Raised exceptions
- Function calls
- Return statements

Using AST analysis allows the system to inspect code structure without executing it.

---

## Existing Test Analysis

Existing tests are also analyzed.

The test extractor can identify:

- Test function names
- Calls made by tests
- Assertions
- Expected exceptions
- Literal values
- Imports
- Aliases

The system can recognize common calling patterns including:

    calculate_discount(...)

    cart.calculate_discount(...)

    from module import calculate_discount as calc
    calc(...)

    import module as cart
    cart.calculate_discount(...)

This information is used to connect tests to the source functions they appear to cover.

---

## Gap Detection

The repository gap analyzer compares source metadata with test metadata.

It detects areas such as:

- Functions with no discovered test calls
- Missing branches
- Missing exception paths
- Missing edge cases

Gap records include:

    function
    qualified_name
    class_name
    is_method
    is_async
    source_file
    covering_tests
    missing_branches
    missing_exceptions
    edge_case_gaps
    confidence
    confidence_label
    reason

---

## Edge Case Detection

Additional edge-case detection looks for patterns such as:

- `none_input`
- `empty_input`
- `boundary`
- `state_or_value`
- `dependency_failure`
- `timeout_or_retry`

These signals help create more targeted test plans.

---

## Confidence Levels

Detected gaps are classified using confidence levels.

### High

Used when no discovered test calls the function.

    confidence: high
    confidence_label: definitely

### Medium

Used when explicit evidence suggests a branch, exception, or distinctive value is missing.

    confidence: medium
    confidence_label: probably

### Low

Used when a finding is based on conservative branch heuristics.

    confidence: low
    confidence_label: uncertain

Low-confidence findings are intended for manual review.

---

## Test Planning

Detected gaps are converted into structured test plans.

A plan may describe:

- What should be tested
- Why the test is needed
- Representative inputs
- Expected behavior
- Gap type
- Gap reference

Test planning can be performed by:

- Google Gemini
- Deterministic fallback planner

---

## Gemini Integration

If a Gemini API key is configured, Gemini can generate structured test plans.

Gemini is optional.

If Gemini is unavailable, incorrectly configured, or returns an unusable result, Test Gap Finder falls back to its deterministic planner.

This prevents the application from depending entirely on an external AI service.

---

## Test Generation

Structured plans are converted into pytest tests.

The generator focuses on detected gaps instead of generating a completely new test suite.

Generated tests may target:

- Invalid input
- Exception paths
- Boundary values
- Empty values
- Special branch values
- Other detected edge cases

---

## Validation

Generated tests are validated before execution.

Only validated generated tests are passed to the test runner.

This provides a safety and quality boundary between generation and execution.

---

## Execution Safety

Test Gap Finder distinguishes between trusted local repositories and external GitHub repositories.

### Local Repository

    source_type: local
    execution_mode: trusted_local
    execution_allowed: true

Trusted local repositories may proceed through:

- Validation
- pytest collection
- Test execution
- Coverage measurement

### GitHub Repository

    source_type: github
    execution_mode: static_only
    execution_allowed: false

External GitHub repositories may be:

- Cloned temporarily
- Read
- Parsed
- Analyzed
- Used to generate suggestions

They are not:

- Imported
- Collected through pytest
- Executed
- Run with generated tests

The temporary clone itself is not a sandbox. Safety comes from preventing external code from reaching the execution stage.

---

## Test Runner

For trusted local repositories, the runner can:

- Execute existing tests
- Execute validated generated tests
- Count passed tests
- Count failed tests
- Measure coverage before
- Measure coverage after
- Return file-level coverage details

Test execution includes a timeout so that a hanging test process can be stopped.

---

## Potential Bug Detection

A generated test can be surfaced as a potential bug when:

1. The test is valid
2. pytest collects it successfully
3. The test executes
4. The test fails against the target implementation

This distinguishes a malformed generated test from a valid generated test that may have exposed unexpected behavior.

---

## Backend

The backend uses FastAPI.

Its responsibilities include:

- API routing
- Repository analysis orchestration
- Execution policy selection
- History storage
- Returning structured analysis results

Main endpoints include:

    GET /health
    POST /analyze
    GET /history
    GET /history/{entry_id}
    PATCH /history/{entry_id}
    DELETE /history/{entry_id}

---

## Frontend

The frontend uses Angular and Angular Material.

It displays:

- Repository information
- File counts
- Detected gaps
- Confidence levels
- Generated tests
- Coverage changes
- Test results
- Static-analysis-only status
- Analysis history

---

## Data Storage

Analysis history is stored locally using SQLite.

The runtime database is stored under:

    backend/data/

and is excluded from source control.

---

## Core Design Principle

The central architectural principle is separating:

    understanding code

from:

    executing code

This allows Test Gap Finder to inspect external repositories safely while restricting execution to trusted local repositories.
