import os
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

from analyzer.test_generation.test_validator import validate_generated_tests

# Legacy generator kept available for fallback (not used by the main flow).
from analyzer.test_generation.test_generator import generate_tests_legacy  # noqa: F401
from analyzer.runner.test_runner import run_tests

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


@app.post("/analyze")
def analyze(request: AnalyzeRequest):
    repo = request.repository_url

    if not os.path.isdir(repo):
        raise HTTPException(status_code=400, detail=f"Repository path not found: {repo}")

    # Structural metrics (counts only)
    scan = scan_repository(repo)

    # Discover source and test files
    discovered = discover_files(repo)
    source_files: list[str] = discovered["source_files"]
    test_files: list[str] = discovered["test_files"]

    # Unique source directories (for coverage measurement)
    source_dirs = list({str(Path(f).parent) for f in source_files})

    # -----------------------------------------------------------------------
    # Main pipeline: gaps → test_plans → generated_tests → test runner
    # -----------------------------------------------------------------------

    # Step 1 — generic repository-level gap records (used in the API response)
    gap_records = analyze_repository_gaps(repo)

    # Step 2 — structured test plans (one entry per gap function)
    test_plans = generate_test_plan(repo)

    # Step 3 — plan-driven test generation
    generated_tests, unsupported_plans = generate_tests_from_plans(test_plans)

    # Step 4 — build the generated pytest module
    module_text = generate_test_module_from_plans(test_plans, source_files)

    # Step 5 — validate generated tests before execution
    validation = validate_generated_tests(
        generated_tests=generated_tests,
        module_text=module_text,
        repo_path=repo,
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
            "potential_bug_findings": [],
            "stdout": "",
            "stderr": "No generated tests passed validation.",
        }

    return {
        "repository": repo,
        "status": "scanned",
        "python_files": scan["python_files"],
        "test_files": scan["test_files"],
        "has_tests_folder": scan["has_tests_folder"],
        "discovered_source_files": source_files,
        "discovered_test_files": test_files,
        "gaps": gap_records,
        "test_plans": test_plans,
        "generated_tests": generated_tests,
        "unsupported_plans": unsupported_plans,
        "validation_results": validation["validation_results"],
        "validation_summary": {
            "valid": len(validation["valid_tests"]),
            "invalid": len(validation["invalid_tests"]),
            "collection_success": validation["collection"]["success"],
        },
        "test_results": test_results,
    }