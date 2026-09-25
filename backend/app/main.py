import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from analyzer.code_analysis.repo_scanner import scan_repository
from analyzer.gap_detection.gap_detector import detect_gaps
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
    scan = scan_repository(repo)

    source_file = os.path.join(repo, "src", "cart.py")
    test_file = os.path.join(repo, "tests", "test_cart.py")
    gaps = detect_gaps(source_file, test_file)

    generated_tests = generate_tests(gaps)
    module_text = generate_test_module(gaps)
    test_results = run_tests(module_text, repo)

    return {
        "repository": repo,
        "status": "scanned",
        "python_files": scan["python_files"],
        "test_files": scan["test_files"],
        "has_tests_folder": scan["has_tests_folder"],
        "gaps": gaps,
        "generated_tests": generated_tests,
        "test_results": test_results,
    }
