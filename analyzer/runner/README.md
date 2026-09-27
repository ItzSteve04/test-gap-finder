# Test Runner

This package runs tests and measures coverage for trusted local repositories.

External GitHub repository code does not reach this execution stage.

---

## Responsibilities

The runner can:

- Execute existing pytest tests
- Execute validated generated tests
- Count passing tests
- Count failing tests
- Measure coverage before generated tests
- Measure coverage after generated tests
- Return file-level coverage details
- Identify potential bug findings

---

## Coverage

Coverage information can include:

    file
    statements
    missing
    coverage
    missing_lines

This allows the application to show both overall improvement and more detailed file-level information.

---

## Timeout

Test execution includes a timeout.

If execution takes longer than the configured limit, the process is stopped rather than being left running indefinitely.

---

## Potential Bugs

When a generated test:

1. passes validation
2. is successfully collected
3. executes normally
4. fails against the implementation

the failure can be surfaced as a potential bug finding.

This is different from a malformed generated test that fails validation.