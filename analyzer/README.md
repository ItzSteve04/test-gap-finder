# Analyzer

The `analyzer` package contains the core static-analysis, test-gap detection, test-planning, test-generation, validation, execution, and coverage logic used by Test Gap Finder.

The analyzer is intentionally separated from the FastAPI backend so that the core analysis pipeline can be developed and tested independently from the HTTP API and frontend.

---

## Structure

    analyzer/
    ├── code_analysis/
    ├── gap_detection/
    ├── runner/
    ├── security/
    └── test_generation/

---

## `code_analysis`

This package is responsible for discovering and understanding repository code.

Key responsibilities include:

- Repository scanning
- Python source discovery
- Test file discovery
- Function extraction
- Class method extraction
- Async function extraction
- Function argument extraction
- Branch extraction
- Raised exception extraction
- Function call extraction
- Existing test extraction
- Import and alias detection
- Repository loading

The analyzer uses Python's Abstract Syntax Tree (`ast`) for static analysis.

This allows Test Gap Finder to inspect Python source code without needing to execute it.

---

## Function Extraction

The function extractor can identify:

- Top-level functions
- Async functions
- Class methods
- Async class methods

Extracted metadata can include:

- Function name
- Qualified name
- Class name
- Whether the function is a method
- Whether the function is async
- Arguments
- Branch conditions
- Raised exceptions
- Function calls
- Return statements

Qualified names help distinguish methods that share the same raw function name.

For example:

    Serializer.__init__

and:

    Signer.__init__

can be represented separately.

---

## Test Extraction

Existing test files are analyzed to identify information such as:

- Test function names
- Function calls
- Assertions
- Expected exceptions
- Literal values
- Imports
- Import aliases

The analyzer can recognize common calling styles.

Direct call:

    calculate_discount(...)

Dotted call:

    cart.calculate_discount(...)

Direct import alias:

    from module import calculate_discount as calc
    calc(...)

Module alias:

    import module as cart
    cart.calculate_discount(...)

This allows the gap analyzer to connect source functions to tests more accurately.

---

## `gap_detection`

The gap detection package compares source functions with the existing test suite.

It identifies:

- Functions with no discovered tests
- Missing branch paths
- Missing exception paths
- Missing edge cases
- Functions that appear only partially tested

A gap record can contain:

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

Test Gap Finder includes additional edge-case analysis.

Supported categories include:

- `none_input`
- `empty_input`
- `boundary`
- `state_or_value`
- `dependency_failure`
- `timeout_or_retry`

Examples include:

- Passing `None`
- Passing an empty list or string
- Testing a boundary such as `0`
- Testing a special state or string value
- Testing a dependency failure
- Testing timeout or retry-related behavior

These findings are used to improve the quality of generated test plans.

---

## Confidence Levels

Detected gaps include a confidence rating.

### High

Used when no discovered test calls the function.

Display label:

    definitely

This is the strongest signal that the function is untested.

### Medium

Used when explicit evidence suggests a branch, exception, or distinctive value is not covered.

Display label:

    probably

### Low

Used when the result comes from more conservative branch heuristics and should be reviewed manually.

Display label:

    uncertain

---

## `test_generation`

This package turns detected gaps into structured test plans and generated pytest tests.

The general flow is:

    Gap Records
        |
        v
    Test Planner
        |
        v
    Structured Test Plans
        |
        v
    Plan-Driven Generator
        |
        v
    Generated pytest Tests
        |
        v
    Test Validator

---

## Gemini Test Planning

Test Gap Finder can optionally use Google Gemini to generate structured test plans.

The planner receives information such as:

- Function metadata
- Arguments
- Branch conditions
- Raised exceptions
- Existing tests
- Missing branches
- Missing exceptions
- Confidence
- Edge-case signals

Gemini is used for planning rather than being trusted to directly execute repository code.

---

## Deterministic Fallback

Gemini is optional.

If:

- No Gemini API key exists
- Gemini is unavailable
- The request fails
- The response is invalid
- The provider cannot be reached

Test Gap Finder falls back to a deterministic planner.

This ensures the application remains functional even without an external AI service.

---

## Test Generation

Structured plans are converted into pytest tests.

The generator attempts to create targeted tests for specific missing behavior rather than generating a completely new test suite.

Generated tests may target:

- Exception paths
- Boundary conditions
- Special branch values
- Empty inputs
- Invalid inputs
- Other detected edge cases

---

## Test Validation

Generated tests are validated before execution.

The validator checks whether generated tests are suitable to continue through the pipeline.

Only tests that pass validation are sent to the test runner.

This reduces the chance of malformed generated code affecting test execution.

---

## `runner`

The runner handles execution for trusted local repositories.

It can:

- Measure existing coverage
- Execute existing tests
- Execute validated generated tests
- Parse pytest results
- Compare coverage before and after
- Return detailed coverage data
- Report potential bug findings

---

## Coverage Reporting

Coverage information can include:

- Coverage before generated tests
- Coverage after generated tests
- File-level statistics
- Missing lines
- Statement counts

This makes the impact of generated tests measurable.

---

## Potential Bug Findings

A generated test may be classified as a potential bug when:

1. The test was successfully generated
2. The test passed validation
3. pytest successfully collected it
4. The test executed
5. The test failed against the target implementation

In this situation, the generated test itself may be valid while the application behavior does not match the expected behavior.

The result can therefore be surfaced as a potential bug finding instead of being discarded as an invalid test.

---

## Test Timeout

Test execution includes a timeout.

If a test run exceeds the configured execution period, it is stopped rather than being allowed to hang indefinitely.

This protects the application from long-running or stuck test executions.

---

## `security`

The security package defines whether repository code is allowed to execute.

### Trusted Local Repository

Local repositories use:

    mode: trusted_local
    execution_allowed: true

Trusted local repositories may proceed through:

- Validation
- pytest collection
- Test execution
- Coverage measurement

### External GitHub Repository

External GitHub repositories use:

    mode: static_only
    execution_allowed: false

External repositories may be:

- Downloaded temporarily
- Read
- Parsed
- Analyzed
- Used to produce test suggestions

They are not:

- Imported
- Collected through pytest
- Executed
- Run with generated tests

---

## Design Principle

A key principle of Test Gap Finder is separating:

    understanding code

from:

    executing code

Static AST analysis can therefore be used on external repositories while code execution remains restricted to trusted local repositories.