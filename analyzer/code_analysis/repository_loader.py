"""Resolve local repository paths and clone public GitHub repositories."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


GITHUB_URL_PATTERN = re.compile(
    r"^https://github\.com/"
    r"(?P<owner>[A-Za-z0-9_.-]+)/"
    r"(?P<repo>[A-Za-z0-9_.-]+?)(?:\.git)?/?$"
)


def is_github_url(value: str) -> bool:
    """Return True when *value* looks like a supported GitHub repository URL."""

    return bool(GITHUB_URL_PATTERN.fullmatch(value.strip()))


def _validate_github_url(url: str) -> str:
    """Validate and normalize a public GitHub repository URL."""

    cleaned = url.strip()

    match = GITHUB_URL_PATTERN.fullmatch(cleaned)

    if not match:
        raise ValueError(
            "Unsupported GitHub URL. Expected format: "
            "https://github.com/owner/repository"
        )

    owner = match.group("owner")
    repo = match.group("repo")

    return f"https://github.com/{owner}/{repo}.git"


def _clone_github_repository(url: str, destination: Path) -> None:
    """Clone a GitHub repository using a shallow clone."""

    normalized_url = _validate_github_url(url)

    if shutil.which("git") is None:
        raise RuntimeError(
            "Git is not installed or is not available on PATH."
        )

    result = subprocess.run(
        [
            "git",
            "clone",
            "--depth",
            "1",
            "--single-branch",
            normalized_url,
            str(destination),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )

    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()

        raise RuntimeError(
            f"Unable to clone GitHub repository: {message}"
        )


@contextmanager
def resolve_repository(repository: str) -> Iterator[dict]:
    """Resolve either a local path or public GitHub repository.

    Yields::

        {
            "repo_path": str,
            "source_type": "local" | "github",
            "execution_allowed": bool,
            "original_input": str,
        }

    GitHub repositories are cloned into a temporary directory and removed
    automatically when the context exits.
    """

    value = repository.strip()

    # ---------------------------------------------------------------
    # Local repository
    # ---------------------------------------------------------------

    if os.path.isdir(value):
        yield {
            "repo_path": str(Path(value).resolve()),
            "source_type": "local",
            "execution_allowed": True,
            "original_input": value,
        }
        return

    # ---------------------------------------------------------------
    # GitHub repository
    # ---------------------------------------------------------------

    if is_github_url(value):
        with tempfile.TemporaryDirectory(
            prefix="test_gap_finder_"
        ) as temp_dir:

            clone_path = Path(temp_dir) / "repository"

            _clone_github_repository(
                value,
                clone_path,
            )

            yield {
                "repo_path": str(clone_path.resolve()),
                "source_type": "github",
                "execution_allowed": False,
                "original_input": value,
            }

        return

    raise ValueError(
        "Repository must be an existing local directory or a public "
        "GitHub URL such as https://github.com/owner/repository."
    )