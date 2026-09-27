# Code Analysis

This package contains static-analysis utilities used to understand Python repositories.

The implementation relies primarily on Python's Abstract Syntax Tree (`ast`).

This means source code can be inspected without executing it.

---

## Responsibilities

Code analysis includes:

- Repository scanning
- Python file discovery
- Test file discovery
- Function extraction
- Method extraction
- Async function extraction
- Branch extraction
- Raise extraction
- Call extraction
- Test extraction
- Import analysis
- Alias analysis
- GitHub repository loading

---

## Function Metadata

Extracted source metadata may include:

    name
    qualified_name
    class_name
    is_method
    is_async
    arguments
    branches
    raises
    calls
    returns

This metadata is passed into the gap-analysis and planning stages.

---

## Test Metadata

Existing tests may provide information such as:

    test name
    calls
    assertions
    expected exceptions
    literals
    imports
    aliases

This is used to estimate which source paths are already represented by existing tests.

---

## Static Analysis

A major design goal is to avoid executing repository code merely to understand its structure.

This is especially important for externally cloned GitHub repositories.

External repositories may be parsed and analyzed without being imported or executed.