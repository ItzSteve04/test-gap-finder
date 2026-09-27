# Documentation

This directory contains supporting documentation for the Test Gap Finder project.

It may contain:

- Demo plans
- Architecture notes
- Hackathon material
- Development notes
- Testing notes
- Submission-related documentation

---

## Recommended Demo

The strongest demonstration starts with the included local repository:

    sample_repo

This demonstrates the complete pipeline because local repository code is treated as trusted and may be executed.

---

## Main Demo Result

The key result to present is:

    4 existing tests
    +
    5 generated tests
    =
    9 passing tests

Coverage improves from:

    65% → 92%

for an increase of:

    +27 percentage points

Detected gap functions include:

    calculate_discount
    apply_coupon
    checkout

---

## Suggested Demo Flow

A concise demo can follow this sequence:

    1. Introduce the testing problem
    2. Open Test Gap Finder
    3. Analyze sample_repo
    4. Show the detected gaps
    5. Expand a gap and explain the missing path
    6. Show generated tests
    7. Show 9 passing tests
    8. Show coverage improving from 65% to 92%
    9. Analyze a public GitHub repository
    10. Highlight "Static analysis only"
    11. Show analysis history
    12. Explain how IBM Bob was used during development

---

## GitHub Safety Demo

A useful second demonstration is a public GitHub repository.

Example:

    https://github.com/pallets/itsdangerous

Test Gap Finder should identify it as an external GitHub repository and use:

    static_only

execution mode.

The UI should display:

    Static analysis only

This demonstrates an important safety feature:

- External repository code is inspected
- AST analysis still runs
- Test gaps can still be detected
- Suggestions can still be produced
- External code is not automatically executed

---

## Local vs GitHub

### Local

    source_type: local
    execution_mode: trusted_local
    execution_allowed: true

The full test pipeline may run.

### GitHub

    source_type: github
    execution_mode: static_only
    execution_allowed: false

Only static analysis is performed.

---

## IBM Bob

When explaining IBM Bob in the demo, distinguish between development assistance and runtime functionality.

IBM Bob was used to help the team build the project, including work on:

- Architecture
- Analysis logic
- Debugging
- Test generation
- Refactoring
- Safety
- Integration
- Documentation

Google Gemini is a separate optional runtime integration used for structured test planning.

---

## Video Requirement

For the hackathon submission, keep the demonstration within the required maximum duration.

Make sure most of the video shows the application actually running.

The strongest screen sequence is:

    sample_repo
        |
        v
    3 detected gaps
        |
        v
    5 generated tests
        |
        v
    9 passing tests
        |
        v
    65% → 92%
        |
        v
    GitHub static-only analysis