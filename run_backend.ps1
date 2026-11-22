Set-Location $PSScriptRoot
& "$PSScriptRoot\.venv312\Scripts\python.exe" -m uvicorn main:app --host 127.0.0.1 --port 8000 --loop none
