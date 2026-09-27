# Test Gap Finder Demo Plan

## Target Length

Keep the final video below the hackathon maximum duration.

Aim for approximately:

    2 minutes 30 seconds to 2 minutes 50 seconds

Make sure at least 90 seconds show the application running.

---

## Key Demo Metrics

Use the current verified local demo result:

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

Do not use older demo numbers such as 96% coverage or 6 generated tests.

---

## Demo Repository

Use:

    sample_repo

The main detected functions are:

    calculate_discount
    apply_coupon
    checkout

---

## Suggested Video Flow

### 0:00 - 0:20 — Problem

Explain the problem briefly.

Suggested narration:

"Passing tests do not necessarily mean an application is well tested. Important branches, exception paths, and edge cases can still be completely uncovered. Test Gap Finder analyzes an existing Python codebase and its tests to find those missing cases automatically."

---

### 0:20 - 0:35 — Solution

Show the main Test Gap Finder interface.

Suggested narration:

"Our solution scans a Python repository, identifies meaningful test gaps, generates targeted pytest tests, validates them, and measures the impact on test coverage."

---

### 0:35 - 1:30 — Local Repository Demo

Enter:

    sample_repo

Select:

    Analyze

Show:

- 2 Python files
- 1 test file
- 3 detected gaps

Expand some of the detected gaps.

### `calculate_discount`

Point out missing error cases such as:

    price < 0

and invalid discount percentages.

### `apply_coupon`

Point out missing values such as:

    SAVE20
    FREESHIP

### `checkout`

Point out:

    empty cart
    invalid quantity

Explain that the system is analyzing both source code and existing tests rather than simply looking at raw line coverage.

---

### 1:30 - 2:00 — Generated Tests and Coverage

Show the generated tests.

Then highlight:

    4 existing tests
    5 generated tests
    9 passing tests
    0 failed tests

Show coverage:

    65% → 92%

Explain:

"Test Gap Finder does not just suggest missing tests. For trusted local repositories it validates and executes generated tests, then shows the measurable coverage improvement."

---

### 2:00 - 2:20 — GitHub Safety

Analyze a public GitHub repository.

Example:

    https://github.com/pallets/itsdangerous

Show:

    Static analysis only

Explain:

"External GitHub repositories are treated differently. We clone and statically analyze them, but we do not import or execute untrusted repository code."

---

### 2:20 - 2:35 — History

Briefly show the history sidebar.

Explain that analyses can be:

- Reopened
- Searched
- Renamed
- Deleted

---

### 2:35 - 2:50 — IBM Bob

Show IBM Bob task-session-summary evidence or relevant project material.

Suggested narration:

"We used IBM Bob throughout development to help design, implement, debug, test, refactor, and document the project, including the analyzer pipeline, execution safety, API architecture, and integration work."

---

## Important Messaging

IBM Bob and Gemini have different roles.

### IBM Bob

IBM Bob helped the team build the project.

### Google Gemini

Gemini is an optional runtime provider used for structured test planning.

If Gemini is unavailable:

    deterministic planner fallback

is used automatically.

Do not say that IBM Bob generates the application's runtime tests.

---

## Strong Closing Line

"Test Gap Finder finds the tests your code is missing, generates targeted pytest cases, and proves their impact with before-and-after coverage."