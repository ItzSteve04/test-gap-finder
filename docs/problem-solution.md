# Problem & Solution Statement

Modern software teams rely heavily on automated testing, but a passing test suite can create a false sense of confidence. Developers often know their overall coverage percentage, yet still lack visibility into which important branches, exception paths, boundary values, and edge cases are not being tested. Finding these gaps manually requires developers to inspect both application code and existing tests, understand how they relate, and then design additional tests. This becomes increasingly difficult as a codebase grows.

Test Gap Finder addresses this problem by analyzing a Python repository and its existing test suite together. It uses static Python AST analysis to extract functions, methods, branches, exceptions, calls, imports, aliases, and existing test behavior. The application then compares the source code with the tests to identify likely gaps and assigns confidence levels explaining how certain each finding is.

Instead of stopping at detection, Test Gap Finder converts identified gaps into structured test plans and targeted pytest tests. Google Gemini can optionally assist with structured test planning, while a deterministic fallback ensures that the core application continues to work without an external AI service. Generated tests are validated before execution.

For trusted local repositories, Test Gap Finder can execute the validated tests and measure coverage before and after generation. This allows developers to see the actual impact of the additional tests. In our included demonstration repository, the tool increases the suite from 4 existing tests to 9 passing tests and improves coverage from 65% to 92%.

Safety is also built into the workflow. Public GitHub repositories can be cloned and analyzed, but external repository code is never automatically imported or executed. These repositories operate in static-analysis-only mode.

The target users are developers, students, reviewers, and engineering teams who want faster feedback on test quality. Rather than simply reporting a coverage percentage or generating generic tests, Test Gap Finder links source-code structure, existing test behavior, gap detection, test generation, validation, execution, and measurable coverage improvement in one workflow.
