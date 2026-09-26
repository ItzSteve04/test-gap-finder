import os
import subprocess
from pathlib import Path

from dotenv import load_dotenv

# Load variables from a local .env file when present.
# Existing environment variables are never overwritten (override=False).
# This is a no-op in production where the .env file is absent.
load_dotenv(override=False)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from analyzer.code_analysis.repo_scanner import scan_repository, discover_files
from analyzer.gap_detection.repo_gap_analyzer import analyze_repository_gaps
from analyzer.test_generation.planner import generate_test_plan
from analyzer.test_generation.plan_driven_generator import (
    generate_tests_from_plans,
    generate_test_module_from_plans,
)

from analyzer.security.execution_policy import get_execution_policy

from analyzer.test_generation.test_validator import validate_generated_tests

from analyzer.code_analysis.repository_loader import resolve_repository

# Legacy generator kept available for fallback (not used by the main flow).
from analyzer.test_generation.test_generator import generate_tests_legacy  # noqa: F401
from analyzer.runner.test_runner import run_tests, measure_coverage_before

app = FastAPI(title="Test Gap Finder API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class AnalyzeRequest(BaseModel):
    repository_url: str


@app.get("/health")
def health():
    return {"status": "ok"}


# The project root is one level above this file (backend/app/main.py → project root).
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _analyze_repository(repo: str, *, execution_allowed: bool, source_type: str):
    if not os.path.isdir(repo):
        raise HTTPException(status_code=400, detail=f"Repository path not found: {repo}")

    # Structural metrics (counts only)
    policy = get_execution_policy(source_type)
    scan = scan_repository(repo)
    discovered = discover_files(repo)

    source_files = discovered["source_files"]
    test_files = discovered["test_files"]

    source_dirs = list({
        str(Path(file_path).parent)
        for file_path in source_files
    })

    gap_records = analyze_repository_gaps(repo)

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

        # Only validated tests are allowed to reach the runner.
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

        execution_mode = policy["mode"]

    # ---------------------------------------------------------------
    # Untrusted cloned repository
    #
    # Do NOT import/collect/run its code yet.
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

        execution_mode = policy["mode"]

    return {
        **scan,
        "source_type": source_type,
        "execution_mode": execution_mode,
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


@app.post("/analyze")
def analyze(request: AnalyzeRequest):
    try:
        with resolve_repository(request.repository_url) as repository:
            policy = get_execution_policy(repository["source_type"])

            return _analyze_repository(
                repository["repo_path"],
                execution_allowed=policy["execution_allowed"],
                source_type=repository["source_type"],
            )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    except subprocess.TimeoutExpired as exc:
        raise HTTPException(
            status_code=504,
            detail="GitHub repository clone timed out.",
        ) from exc