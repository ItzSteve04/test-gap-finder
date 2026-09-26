"""Scans a local repository path and returns structural Python project metrics."""

from __future__ import annotations

import os
from pathlib import Path


IGNORED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    ".env",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".nox",
    ".idea",
    ".vscode",
    "node_modules",
    "dist",
    "build",
    "site",
    "htmlcov",
    ".coverage",
    "coverage",
    "target",
    ".eggs",
    "eggs",
}

TEST_DIR_NAMES = {
    "test",
    "tests",
}


def _is_test_file(filename: str) -> bool:
    """Return True if filename matches common pytest test-file conventions."""
    name = filename.lower()

    return (
        name.startswith("test_")
        or name.endswith("_test.py")
    )


def _is_inside_test_dir(path: Path, repo_root: Path) -> bool:
    """Return True when a file lives somewhere under test/ or tests/."""
    try:
        relative = path.relative_to(repo_root)
    except ValueError:
        return False

    return any(part.lower() in TEST_DIR_NAMES for part in relative.parts[:-1])


def _should_ignore_dir(dirname: str) -> bool:
    """Return True for directories that should not be analyzed."""
    return dirname.lower() in {name.lower() for name in IGNORED_DIRS}


def discover_files(repo_path: str) -> dict:
    """Recursively discover Python source and test files.

    This does not assume any particular project structure such as ``src/`` or
    ``app/``. Any Python file anywhere in the repository can be discovered,
    provided it is not inside an ignored directory.

    A Python file is considered a test when either:

    - its filename matches ``test_*.py``
    - its filename matches ``*_test.py``
    - it lives anywhere underneath a directory named ``test`` or ``tests``

    Args:
        repo_path:
            Absolute or relative path to the repository root.

    Returns:
        Dict containing sorted absolute source and test file paths.
    """

    root = Path(repo_path).resolve()

    source_files: list[str] = []
    test_files: list[str] = []

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            dirname
            for dirname in dirnames
            if not _should_ignore_dir(dirname)
        ]

        current_dir = Path(dirpath)

        for filename in filenames:
            if not filename.lower().endswith(".py"):
                continue

            full_path = (current_dir / filename).resolve()

            is_test = (
                _is_test_file(filename)
                or _is_inside_test_dir(full_path, root)
            )

            if is_test:
                test_files.append(str(full_path))
            else:
                source_files.append(str(full_path))

    source_files.sort()
    test_files.sort()

    return {
        "source_files": source_files,
        "test_files": test_files,
    }


def scan_repository(repo_path: str) -> dict:
    """Scan a local repository and return basic Python project metrics."""

    root = Path(repo_path).resolve()

    discovered = discover_files(str(root))

    source_files = discovered["source_files"]
    test_files = discovered["test_files"]

    has_tests_folder = False

    for dirpath, dirnames, _ in os.walk(root):
        dirnames[:] = [
            dirname
            for dirname in dirnames
            if not _should_ignore_dir(dirname)
        ]

        if any(dirname.lower() in TEST_DIR_NAMES for dirname in dirnames):
            has_tests_folder = True
            break

    return {
        "python_files": len(source_files) + len(test_files),
        "test_files": len(test_files),
        "has_tests_folder": has_tests_folder,
    }