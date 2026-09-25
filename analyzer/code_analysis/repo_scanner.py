"""Scans a local repository path and returns basic structural metrics."""

import os

IGNORED_DIRS = {
    ".venv", "venv", "node_modules", "__pycache__", ".git", "dist", "build",
}


def scan_repository(repo_path: str) -> dict:
    """Scan a local repository and return basic metrics.

    Skips common generated/dependency directories (see IGNORED_DIRS).

    Args:
        repo_path: Absolute or relative path to the repository root.

    Returns:
        A dict with:
            - python_files (int): total .py files found
            - test_files (int): .py files whose name starts with "test_" or ends with "_test.py"
            - has_tests_folder (bool): whether a directory named "tests" or "test" exists
    """
    python_files = 0
    test_files = 0
    has_tests_folder = False

    for dirpath, dirnames, filenames in os.walk(repo_path):
        # Prune ignored directories in-place so os.walk won't descend into them.
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]

        if not has_tests_folder:
            has_tests_folder = any(d in ("tests", "test") for d in dirnames)

        for filename in filenames:
            if filename.endswith(".py"):
                python_files += 1
                if filename.startswith("test_") or filename.endswith("_test.py"):
                    test_files += 1

    return {
        "python_files": python_files,
        "test_files": test_files,
        "has_tests_folder": has_tests_folder,
    }
