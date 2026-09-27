# Gap Detection

This package identifies likely gaps between Python source code and its existing tests.

It compares extracted source metadata against extracted test metadata.

---

## Gap Types

The analyzer can identify:

- Functions with no discovered test calls
- Missing branch conditions
- Missing exception paths
- Missing boundary tests
- Missing empty-input tests
- Missing `None` input tests
- Missing state/value cases
- Dependency failure cases
- Timeout/retry-related cases

---

## Gap Records

A detected gap may include:

    function
    qualified_name
    source_file
    covering_tests
    missing_branches
    missing_exceptions
    edge_case_gaps
    confidence
    confidence_label
    reason

---

## Confidence

### High

No discovered test calls the function.

    confidence: high
    confidence_label: definitely

### Medium

There is explicit evidence that a branch, exception, or distinctive state is not represented.

    confidence: medium
    confidence_label: probably

### Low

The result is based primarily on conservative heuristics.

    confidence: low
    confidence_label: uncertain

Low-confidence results should be reviewed manually.

---

## Edge Cases

The edge-case detector can produce categories including:

    none_input
    empty_input
    boundary
    state_or_value
    dependency_failure
    timeout_or_retry

These findings provide additional context to the test planner.