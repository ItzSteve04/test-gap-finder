"""Execution safety policy for analyzed repositories."""

from __future__ import annotations


def get_execution_policy(source_type: str) -> dict:
    """Return the execution policy for a repository source."""

    if source_type == "local":
        return {
            "execution_allowed": True,
            "mode": "trusted_local",
            "reason": (
                "Local repositories are treated as user-trusted and may "
                "run generated tests."
            ),
            "sandboxed": False,
        }

    if source_type == "github":
        return {
            "execution_allowed": False,
            "mode": "static_only",
            "reason": (
                "Repositories cloned from external GitHub URLs are analyzed "
                "statically and are not imported, collected, or executed."
            ),
            "sandboxed": False,
        }

    return {
        "execution_allowed": False,
        "mode": "static_only",
        "reason": "Unknown repository source type. Execution is disabled.",
        "sandboxed": False,
    }