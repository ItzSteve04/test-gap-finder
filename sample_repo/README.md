# Sample Repository

This directory contains a small Python repository used to demonstrate Test Gap Finder.

It is intentionally designed with incomplete test coverage so that the analyzer can identify meaningful test gaps and generate additional tests.

---

## Structure

    sample_repo/
    ├── src/
    │   └── cart.py
    └── tests/
        └── test_cart.py

---

## Purpose

The sample repository provides a predictable local target for demonstrating the full Test Gap Finder pipeline.

Because it is a trusted local repository, the application can:

- Analyze the source code
- Analyze the existing tests
- Detect test gaps
- Generate targeted tests
- Validate generated tests
- Execute the tests
- Measure coverage before and after

---

## Main Functions

The sample includes functions such as:

    calculate_discount
    apply_coupon
    checkout

The existing tests cover normal behavior but deliberately leave some branches and exception paths untested.

---

## Example Gaps

### `calculate_discount`

Test Gap Finder can identify missing validation paths such as:

    price < 0

and invalid discount percentages.

It can also detect missing exception behavior such as invalid input raising `ValueError`.

---

### `apply_coupon`

The existing tests do not cover every coupon branch.

Examples include:

    SAVE20
    FREESHIP

These are detected as missing state/value-specific paths.

---

### `checkout`

The sample intentionally leaves cases such as:

    empty cart
    invalid quantity

under-tested.

These can be detected as empty-input and boundary-related gaps.

---

## Demonstration Result

A typical complete Test Gap Finder run on this repository produces:

    Python files:       2
    Test files:         1
    Detected gaps:      3
    Existing tests:     4
    Generated tests:    5
    Passing tests:      9
    Failed tests:       0
    Coverage before:   65%
    Coverage after:    92%
    Improvement:       +27 percentage points

---

## Run the Demo

Start both the FastAPI backend and Angular frontend.

Then enter:

    sample_repo

into the repository field and select:

    Analyze

Because `sample_repo` is a trusted local repository, generated tests may be validated and executed.

---

## Why This Repository Exists

The sample is intentionally small so that the entire analysis can be understood during a short demonstration.

It gives the project a repeatable example showing:

    Existing Tests
        |
        v
    Detected Gaps
        |
        v
    Generated Tests
        |
        v
    More Passing Tests
        |
        v
    Higher Coverage

The sample is intended for demonstration and development rather than as a production application.
