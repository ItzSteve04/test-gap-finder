"""Primary API routes for Test Gap Finder."""

from __future__ import annotations

import subprocess
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from analyzer.code_analysis.repository_loader import resolve_repository
from backend.app.models import history_store
from backend.app.models.analyze import AnalyzeRequest
from backend.app.services.analysis_service import analyze_repository


router = APIRouter()


def _derive_title(repository: str) -> str:
    """Derive a short default title from the repository input."""

    repo = repository.strip()

    if repo.endswith(".git"):
        repo = repo[:-4]

    segment = (
        repo.rstrip("/\\")
        .rsplit("/", 1)[-1]
        .rsplit("\\", 1)[-1]
    )

    title = segment or repo

    if len(title) > 60:
        title = title[:59] + "…"

    return title


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/analyze")
def analyze(request: AnalyzeRequest):
    entry_id = uuid.uuid4().hex
    history_entry_created = False

    try:
        with resolve_repository(request.repository_url) as repository:
            source_type = repository["source_type"]
            title = _derive_title(request.repository_url)

            history_store.create_running_entry(
                entry_id,
                title,
                request.repository_url,
                source_type,
            )
            history_entry_created = True

            try:
                result = analyze_repository(
                    repository["repo_path"],
                    source_type=source_type,
                )
            except (
                ValueError,
                RuntimeError,
                subprocess.TimeoutExpired,
            ) as exc:
                history_store.fail_entry(entry_id, str(exc))
                raise

            history_store.complete_entry(entry_id, result)

            created_at = datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )

            entry = history_store.get_entry(entry_id)

            if entry:
                created_at = entry.get(
                    "created_at",
                    created_at,
                )

            return {
                **result,
                "id": entry_id,
                "title": title,
                "created_at": created_at,
            }

    except ValueError as exc:
        if history_entry_created:
            history_store.fail_entry(entry_id, str(exc))

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except RuntimeError as exc:
        if history_entry_created:
            history_store.fail_entry(entry_id, str(exc))

        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    except subprocess.TimeoutExpired as exc:
        if history_entry_created:
            history_store.fail_entry(entry_id, str(exc))

        raise HTTPException(
            status_code=504,
            detail="GitHub repository clone timed out.",
        ) from exc