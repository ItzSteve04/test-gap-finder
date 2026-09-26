"""API routes for saved analysis history."""

from fastapi import APIRouter, HTTPException

from backend.app.models import history_store
from backend.app.models.history import RenameRequest


history_router = APIRouter()


@history_router.get("/history")
def list_history(
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    return {
        "items": history_store.list_entries(
            q,
            limit,
            offset,
        )
    }


@history_router.get("/history/{entry_id}")
def get_history_entry(entry_id: str):
    entry = history_store.get_entry(entry_id)

    if entry is None:
        raise HTTPException(
            status_code=404,
            detail="Analysis not found",
        )

    result = dict(entry)

    payload = result.pop(
        "result_json",
        None,
    )

    if isinstance(payload, dict):
        result = {
            **payload,
            **result,
        }

    return result


@history_router.patch("/history/{entry_id}")
def rename_history_entry(
    entry_id: str,
    request: RenameRequest,
):
    title = request.title.strip()

    if not title:
        raise HTTPException(
            status_code=400,
            detail="Title cannot be empty",
        )

    if not history_store.rename_entry(
        entry_id,
        title,
    ):
        raise HTTPException(
            status_code=404,
            detail="Analysis not found",
        )

    return {
        "id": entry_id,
        "title": title,
    }


@history_router.delete("/history/{entry_id}")
def delete_history_entry(entry_id: str):
    if not history_store.delete_entry(entry_id):
        raise HTTPException(
            status_code=404,
            detail="Analysis not found",
        )

    return {
        "id": entry_id,
        "deleted": True,
    }