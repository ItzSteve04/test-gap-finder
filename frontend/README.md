# Frontend

The Test Gap Finder frontend is an Angular application that provides a visual interface for repository analysis.

It communicates with the FastAPI backend and displays test-gap findings in a developer-friendly dashboard.

---

## Technology

The frontend uses:

- Angular
- TypeScript
- Angular Material
- Angular signals
- Angular HTTP client

---

## Features

The interface can display:

- Repository name or path
- Analysis status
- Python file count
- Test file count
- Detected test gaps
- Confidence levels
- Missing branches
- Missing exceptions
- Generated tests
- Tests passed
- Tests failed
- Coverage before
- Coverage after
- Coverage improvement
- Static-analysis-only status
- Previous analysis history

---

## Backend URL

During local development, the frontend communicates with the backend at:

    http://127.0.0.1:8000

The Angular development server normally runs at:

    http://localhost:4200

Both services should be running at the same time.

---

# Prerequisites

Install Node.js LTS.

Verify Node:

    node --version

Verify npm:

    npm.cmd --version

If normal `npm` works in your PowerShell installation, you can also use:

    npm --version

---

# Install Dependencies

From the project root:

    cd frontend

Install packages:

    npm.cmd install

If plain `npm` works on your machine:

    npm install

---

# Start the Development Server

Run:

    npm.cmd start

If the project does not start through the npm script, you can use Angular CLI directly:

    npx.cmd ng serve

Then open:

    http://localhost:4200

---

# Production Build

To verify that the frontend builds successfully:

    npm.cmd run build

A successful build should finish with a message similar to:

    Application bundle generation complete.

Build output is created under:

    dist/

Angular may also show bundle-budget warnings.

Warnings do not necessarily indicate a failed build.

Check that the command completes successfully.

---

# Using the Application

Enter a repository into the repository input field and select:

    Analyze

You can analyze either:

- A trusted local repository
- A public GitHub repository URL

---

## Local Repository Example

Use the included demo repository:

    sample_repo

For trusted local repositories, the frontend can show:

- Coverage before
- Coverage after
- Coverage improvement
- Tests passed
- Tests failed
- Detected gaps
- Generated tests

A typical demo result is:

    Coverage Before: 65%
    Coverage After:  92%
    Tests Passed:    9
    Tests Failed:    0

---

## GitHub Repository Example

Example:

    https://github.com/pallets/itsdangerous

External repositories are analyzed statically.

Their code is intentionally not executed.

The interface therefore displays:

    Static analysis only

instead of displaying unmeasured coverage or test counts as real execution results.

---

# Detected Gaps

Each gap can show information such as:

- Function name
- Confidence
- Reason
- Missing branches
- Missing exceptions

Confidence values may include:

    high
    medium
    low

These correspond to stronger or weaker evidence that a detected test gap exists.

---

# Generated Tests

Generated tests are displayed in expandable panels.

Each generated item can include:

- Target function
- Gap being addressed
- Generated pytest code

---

# Analysis History

The history sidebar supports:

- Searching previous analyses
- Opening a previous analysis
- Renaming entries
- Deleting entries
- Starting a new analysis

History data is stored by the backend.

---

# Troubleshooting

## `npm` is not recognized

Make sure Node.js LTS is installed.

On Windows, you can install it using:

    winget install --id OpenJS.NodeJS.LTS -e --source winget

Then reopen PowerShell.

---

## `npm` fails because of PowerShell script policy

Try:

    npm.cmd install

instead of:

    npm install

You can also temporarily allow scripts in the current PowerShell session:

    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

---

## Backend Connection Fails

Make sure the backend is running at:

    http://127.0.0.1:8000

Check:

    http://127.0.0.1:8000/health

The frontend development server should be running at:

    http://localhost:4200