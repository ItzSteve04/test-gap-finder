# start.ps1 — Run the backend with the correct PYTHONPATH
$env:PYTHONPATH = "$PSScriptRoot"
& "$PSScriptRoot\venv\Scripts\Activate.ps1"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
