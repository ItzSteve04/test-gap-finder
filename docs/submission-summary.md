# Test Gap Finder — Submission Summary

## Project Title

Test Gap Finder

---

## Short Description

Test Gap Finder analyzes Python repositories to identify meaningful test gaps, generate targeted pytest tests, validate and run them safely, and show the measurable coverage impact in a developer-friendly web dashboard.

---

## Long Description — Problem & Solution Statement

Modern software teams rely heavily on automated testing, but a passing test suite can create a false sense of confidence. Developers often know their overall coverage percentage, yet still lack visibility into which important branches, exception paths, boundary values, and edge cases are not being tested. Finding these gaps manually requires developers to inspect both application code and existing tests, understand how they relate, and then design additional tests. This becomes increasingly difficult as a codebase grows.

Test Gap Finder addresses this problem by analyzing a Python repository and its existing test suite together. It uses static Python AST analysis to extract functions, methods, branches, exceptions, calls, imports, aliases, and existing test behavior. The application then compares the source code with the tests to identify likely gaps and assigns confidence levels explaining how certain each finding is.

Instead of stopping at detection, Test Gap Finder converts identified gaps into structured test plans and targeted pytest tests. Google Gemini can optionally assist with structured test planning, while a deterministic fallback ensures that the core application continues to work without an external AI service. Generated tests are validated before execution.

For trusted local repositories, Test Gap Finder can execute the validated tests and measure coverage before and after generation. This allows developers to see the actual impact of the additional tests. In our included demonstration repository, the tool increases the suite from 4 existing tests to 9 passing tests and improves coverage from 65% to 92%.

Safety is also built into the workflow. Public GitHub repositories can be cloned and analyzed, but external repository code is never automatically imported or executed. These repositories operate in static-analysis-only mode.

The target users are developers, students, reviewers, and engineering teams who want faster feedback on test quality. Rather than simply reporting a coverage percentage or generating generic tests, Test Gap Finder links source-code structure, existing test behavior, gap detection, test generation, validation, execution, and measurable coverage improvement in one workflow.

---

## IBM Bob Usage Statement

IBM Bob was used throughout the development of Test Gap Finder as a development assistant across architecture, implementation, debugging, testing, refactoring, and documentation.

The team used IBM Bob while designing the overall project structure and breaking the problem into separate stages: repository scanning, Python source analysis, existing-test analysis, test-gap detection, test planning, test generation, validation, execution, and coverage reporting.

Bob assisted during development of the Python static-analysis pipeline. This included work around extracting functions, methods, async functions, branches, exceptions, calls, and test metadata using Python's AST. It also helped the team improve matching between source functions and existing tests, including direct calls, dotted calls, imported aliases, and module aliases.

IBM Bob was also used while developing the gap-detection logic. The team iterated on confidence levels, edge-case detection, branch analysis, exception-path detection, and the structured records returned by the analyzer.

During test-generation development, Bob helped with the planner/provider architecture, deterministic fallback behavior, generated-test validation, pytest execution, coverage measurement, timeout handling, and identifying failures that may represent potential bugs in the target implementation.

Bob contributed to the safety design for external repositories. The project distinguishes trusted local repositories from GitHub repositories, allowing full execution for trusted local code while restricting external repositories to static analysis only.

The team also used Bob during backend refactoring, frontend/backend integration, debugging API responses, analysis history, GitHub repository handling, Gemini integration, documentation, local setup instructions, and final hackathon preparation.

IBM Bob was used as a tool to help the team build Test Gap Finder. It is separate from Google Gemini, which is an optional runtime integration used by the application to generate structured test plans. If Gemini is unavailable, Test Gap Finder automatically uses its deterministic planning fallback.

---

## Technology Tags

- IBM Bob 2.0
- Python
- FastAPI
- Angular
- TypeScript
- Angular Material
- pytest
- pytest-cov
- Python AST
- Google Gemini
- SQLite
- GitHub

---

## Category Tags

- Developer Tools
- Software Testing
- AI-Assisted Development
- Code Quality
- Test Automation
- Static Analysis
- Quality Assurance
- DevTools

---

## Public Repository

https://github.com/ItzSteve04/test-gap-finder

---

## Demo Application Platform

Angular frontend + FastAPI backend

---

## Application URL

Add deployed public URL here before submission.

---

## Key Demo Metrics

- 2 Python files
- 1 test file
- 3 detected gaps
- 4 existing tests
- 5 generated tests
- 9 passing tests
- 0 failed tests
- 65% coverage before
- 92% coverage after
- +27 percentage points

---

## Core Pitch

Test Gap Finder finds the tests your code is missing, generates targeted pytest cases, and proves their impact with before-and-after coverage.