# Analyzer

The `analyzer` folder contains the core Python logic responsible for identifying missing or weak test coverage in a repository.

This part of the project does the actual analysis work behind Test Gap Finder.

Its role is to inspect the source code, understand the existing tests, examine test coverage, identify potentially important untested behaviour, generate targeted tests, and run those tests.

## Main Responsibilities

The analyzer is responsible for:

- inspecting repository source code
- inspecting existing tests
- identifying functions, branches, conditions, and error paths
- reading test coverage information
- detecting potentially important test gaps
- generating targeted tests for those gaps
- running existing and generated tests
- collecting pass/fail results
- collecting coverage results
- returning structured findings to the backend

## Folder Structure

### `code_analysis/`

Responsible for analyzing the source code of the repository.

This area will be used to understand the structure and behaviour of the code being tested.

It may identify things such as:

- functions
- classes
- conditional branches
- error handling
- exceptions
- boundary conditions
- important logic paths

The output from this analysis helps the rest of the system understand what behaviour may need testing.

---

### `coverage_analysis/`

Responsible for analyzing existing test coverage.

This area examines which parts of the source code are already exercised by the current test suite.

It may identify:

- files with low coverage
- functions with no coverage
- branches that are never executed
- lines that are not currently tested
- areas where coverage is weaker than expected

Coverage information is one of the inputs used when deciding where test gaps exist.

---

### `gap_detection/`

Responsible for identifying missing or weak test cases.

This area combines information from the source-code analysis, existing tests, and coverage analysis.

Its purpose is to answer questions such as:

- Which important code paths are not tested?
- Are edge cases missing?
- Are error-handling paths covered?
- Are boundary conditions tested?
- Is risky logic being ignored by the current test suite?

Example:

```text
Function:
process_payment()

Existing test:
- successful payment

Potential gaps:
- insufficient funds
- zero amount
- negative amount
- payment provider timeout
