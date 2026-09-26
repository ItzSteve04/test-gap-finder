"""Request models for analysis history."""

from pydantic import BaseModel


class RenameRequest(BaseModel):
    title: str