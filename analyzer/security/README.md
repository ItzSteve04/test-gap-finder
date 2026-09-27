# Security

This package defines Test Gap Finder's repository execution policy.

The application makes a deliberate distinction between trusted local repositories and repositories cloned from external GitHub URLs.

---

## Local Repositories

Local repositories use:

    source_type: local
    execution_mode: trusted_local
    execution_allowed: true

Local repository code is treated as user-trusted.

This allows Test Gap Finder to:

- Validate generated tests
- Collect tests with pytest
- Execute tests
- Measure coverage

---

## GitHub Repositories

External GitHub repositories use:

    source_type: github
    execution_mode: static_only
    execution_allowed: false

The application can still:

- Clone the repository temporarily
- Discover files
- Parse Python AST
- Analyze existing tests
- Detect test gaps
- Create test suggestions

It does not:

- Import target code
- Execute target code
- Collect target tests
- Run generated tests

---

## Important Note

The temporary clone directory is not itself a security sandbox.

Safety comes from the execution policy preventing externally cloned code from being executed.

---

## Timeout Protection

Trusted local test execution also includes a timeout so that a hanging test process can be stopped.