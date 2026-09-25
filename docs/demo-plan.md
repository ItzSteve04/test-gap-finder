# Demo Plan

## Goal

Demonstrate how Test Gap Finder improves the developer testing workflow by automatically identifying missing tests, generating targeted pytest tests, running them, and showing measurable coverage improvement.

The current demo uses the controlled `sample_repo` so the workflow is predictable and easy to explain.

## Demo Flow

### 1. Introduce the problem

Developers often have test suites that appear healthy but still miss important branches, edge cases, and error-handling paths.

Finding these gaps manually can take time, especially in unfamiliar codebases.

Test Gap Finder automates that process.

### 2. Show the sample repository

The sample project contains:

- Python source code
- an existing pytest test suite
- intentionally missing test cases
- branches and validation paths that are not currently tested

The existing tests all pass, but the test suite is incomplete.

### 3. Start analysis

The user provides the repository/path and starts the analysis.

The frontend sends a request to:

POST /analyze

The backend then starts the full analysis workflow.

### 4. Scan the repository

The repository scanner identifies basic project information such as:

- number of Python files
- number of existing test files
- whether a tests folder exists

Current sample result:

Python files: 2  
Test files: 1  
Tests folder: Yes

### 5. Detect missing tests

The gap detector analyzes the source code and existing tests.

It identifies untested logic such as:

- untested error paths
- missing validation cases
- untested branches
- missing boundary conditions

For the current sample repository, gaps are detected across functions such as:

- calculate_discount
- apply_coupon
- checkout

### 6. Generate targeted tests

The detected gaps are passed to the test generator.

The system generates unique pytest test suggestions for those missing scenarios.

The current sample produces:

6 unique generated tests

Examples include tests for:

- negative values
- invalid percentage ranges
- specific branch conditions
- empty input
- invalid quantities

### 7. Run the generated tests

The generated tests are written to a temporary test module and executed with pytest.

The temporary file is removed after execution so the original repository is not permanently modified.

Current result:

Generated tests passed: 6  
Generated tests failed: 0

### 8. Show measurable impact

The runner measures test coverage before and after the generated tests are added.

Current sample result:

Coverage before: 65%  
Coverage after: 96%

This demonstrates a measurable improvement in test coverage from targeted test generation.

### 9. Show final results

The frontend should display:

- repository information
- detected test gaps
- generated tests
- pass/fail results
- coverage before
- coverage after
- coverage improvement

The main visual result should make the improvement immediately obvious:

65% → 96%

## Current Technical Flow

Repository  
↓  
Angular Frontend  
↓  
FastAPI Backend  
↓  
Repository Scanner  
↓  
Gap Detection  
↓  
Test Generation  
↓  
pytest Runner  
↓  
Coverage Measurement  
↓  
Results returned to Frontend

## IBM Bob Usage

IBM Bob has been used throughout development to help:

- create the initial FastAPI backend
- build the repository scanner
- improve repository scanning and ignore generated folders
- create the test gap detector
- build the test generator
- remove duplicate generated test scenarios
- build the generated test runner
- integrate the analyzer with the API
- add before/after coverage measurement
- validate components during development

Bob task-session evidence should be stored in the `bob_sessions/` folder for the final submission.

## Demo Message

The core message of the demo is:

> Test Gap Finder reduces the manual effort required to identify missing tests. It analyzes an existing codebase, finds important untested behaviour, generates targeted tests, runs them automatically, and demonstrates measurable improvement in test coverage.

## Current Demo Metrics

Existing tests: 4  
Generated tests: 6  
Generated test results: 6 passed / 0 failed  

Coverage before: 65%  
Coverage after: 96%  
Coverage improvement: +31 percentage points

## Before Final Submission

Before recording the final demo:

- connect the Angular frontend to the backend
- replace the temporary sample repository with a more developer-relevant example if appropriate
- confirm the complete workflow works from the UI
- verify all Bob session evidence is saved
- ensure the public GitHub repository contains no secrets
- rehearse the presentation so it stays under 5 minutes
