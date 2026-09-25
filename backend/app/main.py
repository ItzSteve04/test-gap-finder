from fastapi import FastAPI
from pydantic import BaseModel

from analyzer.code_analysis.repo_scanner import scan_repository

app = FastAPI(title="Test Gap Finder API")


class AnalyzeRequest(BaseModel):
    repository_url: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze")
def analyze(request: AnalyzeRequest):
    scan = scan_repository(request.repository_url)
    return {
        "repository": request.repository_url,
        "status": "scanned",
        "python_files": scan["python_files"],
        "test_files": scan["test_files"],
        "has_tests_folder": scan["has_tests_folder"],
    }
