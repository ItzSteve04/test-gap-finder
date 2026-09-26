# start.ps1 — Run the backend from the repo root so imports resolve correctly.
$repoRoot = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = $repoRoot
& "$PSScriptRoot\.venv\Scripts\Activate.ps1"
Set-Location $repoRoot
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
