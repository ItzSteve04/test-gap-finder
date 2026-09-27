# Test Generation

This package converts detected test gaps into structured test plans and generated pytest tests.

---

## Pipeline

    Detected Gaps
        |
        v
    Planner
        |
        v
    Structured Plans
        |
        v
    Plan-Driven Generator
        |
        v
    Generated pytest Code
        |
        v
    Validator

---

## Planner

The planner decides what should be tested.

Plans may include:

- A title
- Reason for the test
- Representative inputs
- Expected behavior
- Gap type
- Gap reference

The planner does not need to generate executable test code directly.

---

## Gemini Provider

When configured, Google Gemini can be used to produce structured test plans.

Configuration is supplied using:

    GEMINI_API_KEY

Gemini is optional.

---

## Deterministic Planner

A deterministic planner is available as a fallback.

It is used when:

- Gemini is not configured
- Gemini is unavailable
- A Gemini request fails
- The response is unusable

The application can therefore continue functioning without the external AI provider.

---

## Plan-Driven Test Generator

Structured plans are converted into pytest test cases.

The generator targets specific detected gaps instead of attempting to rewrite the entire test suite.

---

## Validation

Generated tests are validated before they are allowed to execute.

Only validated tests continue to the runner for trusted local repositories.