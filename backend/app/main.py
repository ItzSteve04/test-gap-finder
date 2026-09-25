import os

from fastapi import FastAPI
from pydantic import BaseModel

from analyzer.code_analysis.repo_scanner import scan_repository
from analyzer.gap_detection.gap_detector import detect_gaps

app = FastAPI(title="Test Gap Finder API")


class AnalyzeRequest(BaseModel):
    repository_url: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze")
def analyze(request: AnalyzeRequest):
    repo = request.repository_url
    scan = scan_repository(repo)

    source_file = os.path.join(repo, "src", "cart.py")
    test_file = os.path.join(repo, "tests", "test_cart.py")
    gaps = detect_gaps(source_file, test_file)

    return {
        "repository": repo,
        "status": "scanned",
        "python_files": scan["python_files"],
        "test_files": scan["test_files"],
        "has_tests_folder": scan["has_tests_folder"],
        "gaps": gaps,
    }
