# IBM Bob Usage

IBM Bob was used throughout the development of Test Gap Finder as a development assistant across architecture, implementation, debugging, testing, refactoring, and documentation.

The team used IBM Bob while designing the overall project structure and breaking the problem into separate stages: repository scanning, Python source analysis, existing-test analysis, test-gap detection, test planning, test generation, validation, execution, and coverage reporting.

Bob assisted during development of the Python static-analysis pipeline. This included work around extracting functions, methods, async functions, branches, exceptions, calls, and test metadata using Python's AST. It also helped the team improve matching between source functions and existing tests, including direct calls, dotted calls, imported aliases, and module aliases.

IBM Bob was also used while developing the gap-detection logic. The team iterated on confidence levels, edge-case detection, branch analysis, exception-path detection, and the structured records returned by the analyzer.

During test-generation development, Bob helped with the planner/provider architecture, deterministic fallback behavior, generated-test validation, pytest execution, coverage measurement, timeout handling, and identifying failures that may represent potential bugs in the target implementation.

Bob contributed to the safety design for external repositories. The project distinguishes trusted local repositories from GitHub repositories, allowing full execution for trusted local code while restricting external repositories to static analysis only.

The team also used Bob during backend refactoring. The FastAPI application was separated into routes, models, services, utilities, and history storage, making the application easier to maintain and reducing the amount of orchestration logic in the main application entry point.

Bob additionally supported frontend/backend integration, debugging API responses, analysis history, GitHub repository handling, Gemini integration, documentation, local setup instructions, and final hackathon preparation.

IBM Bob was used as a tool to help the team build Test Gap Finder. It is separate from Google Gemini, which is an optional runtime integration used by the application to generate structured test plans. If Gemini is unavailable, Test Gap Finder automatically uses its deterministic planning fallback.

Task-session-summary screenshots from each team member are stored in the `bob_sessions` directory as evidence of IBM Bob usage during development.
