# Test Gap Finder — Presentation Notes

## Slide 1 — Title

Test Gap Finder

Find the tests your code is missing.

Team:
- Dylan Glynn
- Stephen McNeil
- Ben Chadwick

Talking point:

"Test Gap Finder analyzes Python code and its existing tests to identify meaningful gaps, generate targeted pytest tests, and show the measurable impact on coverage."

---

## Slide 2 — The Problem

Developers can have a passing test suite while still missing:

- Important branches
- Exception paths
- Boundary cases
- Edge cases
- Entire untested functions

Talking point:

"Coverage percentages alone do not always tell developers what is missing. We wanted to make test gaps concrete and actionable."

---

## Slide 3 — The Solution

Test Gap Finder:

1. Scans the repository
2. Parses Python source and tests using AST
3. Detects likely missing test paths
4. Creates structured test plans
5. Generates pytest tests
6. Validates generated tests
7. Executes trusted local tests
8. Measures coverage improvement

---

## Slide 4 — Demo Result

Using the included sample repository:

- 4 existing tests
- 5 generated tests
- 9 passing tests
- 0 failed tests
- Coverage improved from 65% to 92%

Talking point:

"The key value is that the tool does not stop at suggestions. It can prove the impact of generated tests on a trusted local repository."

---

## Slide 5 — Safety

Trusted local repositories:

- Full validation
- pytest execution
- Coverage measurement

External GitHub repositories:

- Static analysis only
- No importing
- No pytest collection
- No execution

Talking point:

"We deliberately separate understanding code from executing code."

---

## Slide 6 — IBM Bob

IBM Bob assisted with:

- Architecture
- Static analysis
- Gap-detection logic
- Test generation
- Debugging
- Safety design
- Backend refactoring
- Integration
- Documentation

Talking point:

"IBM Bob was used throughout the development process as a coding and engineering assistant."

---

## Slide 7 — Closing

Test Gap Finder combines:

- Static analysis
- Existing test understanding
- Targeted test generation
- Safety controls
- Coverage validation

Closing line:

"Test Gap Finder finds the tests your code is missing, generates targeted pytest cases, and proves their impact with before-and-after coverage."