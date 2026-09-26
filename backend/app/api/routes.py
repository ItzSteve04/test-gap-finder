"""FastAPI routes for Test Gap Finder."""

import subprocess

from fastapi import APIRouter, HTTPException

from analyzer.code_analysis.repository_loader import resolve_repository
from backend.app.models.analyze import AnalyzeRequest
from backend.app.services.analysis_service import analyze_repository


router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/analyze")
def analyze(request: AnalyzeRequest):
    try:
        with resolve_repository(request.repository_url) as repository:
            return analyze_repository(
                repository["repo_path"],
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