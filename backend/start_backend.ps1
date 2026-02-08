$ErrorActionPreference = "Stop"
try {
    Remove-Module PSConsoleReadLine -ErrorAction SilentlyContinue
} catch {}
& ".\venv\Scripts\python.exe" main.py