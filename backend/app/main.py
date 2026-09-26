import os
import subprocess
import uuid
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

from app.models import history_store

# Initialise the SQLite database (creates the file + table if missing).
history_store.init_db()

app = FastAPI(title="Test Gap Finder API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
)


class AnalyzeRequest(BaseModel):
    repository_url: str


class RenameRequest(BaseModel):
    title: str


@app.get("/health")
def health():
    return {"status": "ok"}


# The project root is one level above this file (backend/app/main.py → project root).
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _derive_title(repository: str) -> str:
    """Derive a short default title from the repository input."""
    repo = repository.strip()
    # Strip trailing .git
    if repo.endswith(".git"):
        repo = repo[:-4]
    # Take the last path segment (works for both local paths and GitHub URLs)
    segment = repo.rstrip("/\\").rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    title = segment or repo
    if len(title) > 60:
        title = title[:59] + "…"
    return title


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
    entry_id = uuid.uuid4().hex

    try:
        with resolve_repository(request.repository_url) as repository:
            source_type = repository["source_type"]
            title = _derive_title(request.repository_url)
            history_store.create_running_entry(
                entry_id, title, request.repository_url, source_type
            )

            try:
                result = _analyze_repository(
                    repository["repo_path"],
                    execution_allowed=repository["execution_allowed"],
                    source_type=source_type,
                )
            except (HTTPException, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
                history_store.fail_entry(entry_id, str(exc))
                raise

            history_store.complete_entry(entry_id, result)

            # Retrieve stored metadata so the frontend gets the canonical timestamps.
            from datetime import datetime, timezone
            created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            entry = history_store.get_entry(entry_id)
            if entry:
                created_at = entry.get("created_at", created_at)

            return {**result, "id": entry_id, "title": title, "created_at": created_at}

    except ValueError as exc:
        # resolve_repository raised before we could call create_running_entry
        try:
            history_store.fail_entry(entry_id, str(exc))
        except Exception:
            pass
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except RuntimeError as exc:
        try:
            history_store.fail_entry(entry_id, str(exc))
        except Exception:
            pass
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    except subprocess.TimeoutExpired as exc:
        try:
            history_store.fail_entry(entry_id, str(exc))
        except Exception:
            pass
        raise HTTPException(
            status_code=504,
            detail="GitHub repository clone timed out.",
        ) from exc


# ─── History endpoints ────────────────────────────────────────────────────────

@app.get("/history")
def list_history(q: str | None = None, limit: int = 50, offset: int = 0):
    return {"items": history_store.list_entries(q, limit, offset)}


@app.get("/history/{entry_id}")
def get_history_entry(entry_id: str):
    entry = history_store.get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    # Merge the decoded result_json fields into the top-level response so the
    # frontend can render the same AnalyzeResponse template directly.
    result = dict(entry)
    payload = result.pop("result_json", None)
    if isinstance(payload, dict):
        result = {**payload, **result}
    return result


@app.patch("/history/{entry_id}")
def rename_history_entry(entry_id: str, request: RenameRequest):
    if not request.title.strip():
        raise HTTPException(status_code=400, detail="Title cannot be empty")
    if not history_store.rename_entry(entry_id, request.title.strip()):
        raise HTTPException(status_code=404, detail="Analysis not found")
    return {"id": entry_id, "title": request.title.strip()}


@app.delete("/history/{entry_id}")
def delete_history_entry(entry_id: str):
    if not history_store.delete_entry(entry_id):
        raise HTTPException(status_code=404, detail="Analysis not found")
    return {"id": entry_id, "deleted": True}
