from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Test Gap Finder API")


class AnalyzeRequest(BaseModel):
    repository_url: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze")
def analyze(request: AnalyzeRequest):
    return {
        "repository_url": request.repository_url,
        "status": "mock",
        "test_gap_count": 42,
    }
