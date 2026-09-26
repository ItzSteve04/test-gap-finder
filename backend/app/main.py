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
from analyzer.gap_detection.gap_detector import detect_gaps
from analyzer.gap_detection.repo_gap_analyzer import analyze_repository_gaps
from analyzer.test_generation.planner import generate_test_plan
from analyzer.test_generation.test_generator import generate_tests, generate_test_module
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

    # Build a lookup so each source file can be matched to a test file.
    # Heuristic: a test file matches a source file when the source file's stem
    # appears in the test file's name (e.g. cart.py → test_cart.py).
    def _find_test_for(src_path: str) -> str | None:
        stem = Path(src_path).stem.lower()
        for tf in test_files:
            tf_name = Path(tf).name.lower()
            if stem in tf_name:
                return tf
        return None

    # Generic repository-level gap analysis (used for the API response).
    gap_records = analyze_repository_gaps(repo)

    # Per-file gap detection with the old detect_gaps format — used only to
    # drive generate_tests / run_tests which expect the legacy missing_cases shape.
    legacy_gaps: list[dict] = []
    for src in source_files:
        test_file = _find_test_for(src)
        if test_file is None:
            # No matching test file — pass the source path twice so detect_gaps
            # finds no calls and flags all paths as gaps.
            test_file = src
        file_gaps = detect_gaps(src, test_file)
        for gap in file_gaps:
            gap["source_file"] = src
        legacy_gaps.extend(file_gaps)

    # Unique source directories (for coverage measurement)
    source_dirs = list({str(Path(f).parent) for f in source_files})

    # Generate and run tests (uses legacy missing_cases format — unchanged)
    generated_tests = generate_tests(legacy_gaps)
    module_text = generate_test_module(legacy_gaps)
    test_results = run_tests(
        module_text,
        repo,
        test_files=test_files if test_files else None,
        source_dirs=source_dirs if source_dirs else None,
    )

    # Structured test plans from the generic planner (one entry per gap function)
    test_plans = generate_test_plan(repo)

    return {
        "repository": repo,
        "status": "scanned",
        "python_files": scan["python_files"],
        "test_files": scan["test_files"],
        "has_tests_folder": scan["has_tests_folder"],
        "discovered_source_files": source_files,
        "discovered_test_files": test_files,
        "gaps": gap_records,
        "generated_tests": generated_tests,
        "test_results": test_results,
        "test_plans": test_plans,
    }
