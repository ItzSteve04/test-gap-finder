"""Scans a local repository path and returns basic structural metrics."""

import os

IGNORED_DIRS = {
    ".venv", "venv", "node_modules", "__pycache__", ".git", "dist", "build",
}


def _is_test_file(filename: str) -> bool:
    """Return True if *filename* matches pytest test-file conventions."""
    return filename.startswith("test_") or filename.endswith("_test.py")


def discover_files(repo_path: str) -> dict:
    """Recursively discover Python source and test files in *repo_path*.

    Skips directories listed in :data:`IGNORED_DIRS`.

    Args:
        repo_path: Absolute or relative path to the repository root.

    Returns:
        A dict with:
            - ``source_files`` (list[str]): absolute paths to non-test ``.py`` files
            - ``test_files``   (list[str]): absolute paths to pytest test files
    """
    source_files: list[str] = []
    test_files: list[str] = []

    for dirpath, dirnames, filenames in os.walk(repo_path):
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]
        for filename in filenames:
            if not filename.endswith(".py"):
                continue
            full_path = os.path.join(dirpath, filename)
            if _is_test_file(filename):
                test_files.append(full_path)
            else:
                source_files.append(full_path)

    return {"source_files": source_files, "test_files": test_files}


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
                if _is_test_file(filename):
                    test_files += 1

    return {
        "python_files": python_files,
        "test_files": test_files,
        "has_tests_folder": has_tests_folder,
    }
