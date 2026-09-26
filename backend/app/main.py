"""FastAPI application entry point for Test Gap Finder."""

from dotenv import load_dotenv

load_dotenv(override=False)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.history_routes import history_router
from backend.app.api.routes import router
from backend.app.models import history_store


history_store.init_db()

app = FastAPI(
    title="Test Gap Finder API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
    ],
    allow_methods=[
        "GET",
        "POST",
        "PATCH",
        "DELETE",
    ],
    allow_headers=[
        "Content-Type",
    ],
)

app.include_router(router)
app.include_router(history_router)