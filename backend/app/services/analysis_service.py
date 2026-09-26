"""Repository analysis orchestration service."""

from __future__ import annotations

import os

from analyzer.code_analysis.repo_scanner import (
    discover_files,
    scan_repository,
)
from analyzer.gap_detection.repo_gap_analyzer import (
    analyze_repository_gaps,
)
from analyzer.runner.test_runner import run_tests
from analyzer.security.execution_policy import get_execution_policy
from analyzer.test_generation.plan_driven_generator import (
    generate_test_module_from_plans,
    generate_tests_from_plans,
)
from analyzer.test_generation.planner import generate_test_plan
from analyzer.test_generation.test_validator import (
    validate_generated_tests,
)

from backend.app.utils.paths import get_source_directories


def analyze_repository(repo: str, source_type: str) -> dict:
    """Run the Test Gap Finder pipeline for a resolved repository."""

    if not os.path.isdir(repo):
        raise ValueError(f"Repository path not found: {repo}")

    policy = get_execution_policy(source_type)
    execution_allowed = policy["execution_allowed"]

    # ---------------------------------------------------------------
    # Discovery and static analysis
    # ---------------------------------------------------------------

    scan = scan_repository(repo)
    discovered = discover_files(repo)

    source_files = discovered["source_files"]
    test_files = discovered["test_files"]

    source_dirs = get_source_directories(source_files)

    gap_records = analyze_repository_gaps(repo)

    # ---------------------------------------------------------------
    # Test planning and generation
    # ---------------------------------------------------------------

    test_plans = generate_test_plan(repo)

    generated_tests, unsupported_plans = generate_tests_from_plans(
        test_plans
    )

    module_text = generate_test_module_from_plans(
        test_plans,
        source_files,
    )

    # ---------------------------------------------------------------
    # Trusted local repository
    # ---------------------------------------------------------------

    if execution_allowed:
        validation = validate_generated_tests(
            generated_tests,
            module_text,
            repo,
            test_files=test_files if test_files else None,
        )

        validated_module_text = validation["validated_module_text"]

        if validation["valid_tests"]:
            test_results = run_tests(
                validated_module_text,
                repo,
                test_files=test_files if test_files else None,
                source_dirs=source_dirs if source_dirs else None,
            )
        else:
            test_results = {
                "passed": 0,
                "failed": 0,
                "exit_code": 1,
                "coverage_before": 0.0,
                "coverage_after": 0.0,
                "coverage_details": {
                    "before": [],
                    "after": [],
                },
                "potential_bug_findings": [],
                "stdout": "",
                "stderr": "No generated tests passed validation.",
            }

        validation_results = validation["validation_results"]

        validation_summary = {
            "valid": len(validation["valid_tests"]),
            "invalid": len(validation["invalid_tests"]),
            "collection_success": validation["collection"]["success"],
        }

    # ---------------------------------------------------------------
    # External GitHub repository
    #
    # Static analysis only. No imports, collection, or pytest execution.
    # ---------------------------------------------------------------

    else:
        validation_results = []

        validation_summary = {
            "valid": 0,
            "invalid": 0,
            "collection_success": False,
            "skipped": True,
            "reason": (
                "Generated tests were not collected or executed because "
                "the repository was cloned from an external GitHub URL."
            ),
        }

        test_results = {
            "passed": 0,
            "failed": 0,
            "exit_code": 0,
            "coverage_before": 0.0,
            "coverage_after": 0.0,
            "coverage_details": {
                "before": [],
                "after": [],
            },
            "potential_bug_findings": [],
            "stdout": "",
            "stderr": "",
            "execution_skipped": True,
        }

    return {
        **scan,
        "source_type": source_type,
        "execution_mode": policy["mode"],
        "safety": policy,
        "source_files": source_files,
        "test_files_discovered": test_files,
        "gaps": gap_records,
        "test_plans": test_plans,
        "generated_tests": generated_tests,
        "unsupported_plans": unsupported_plans,
        "validation_results": validation_results,
        "validation_summary": validation_summary,
        "test_results": test_results,
    }