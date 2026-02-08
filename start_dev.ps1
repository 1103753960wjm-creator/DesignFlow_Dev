$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $root "backend"
$clientDir = Join-Path $root "client"
$python = Join-Path $root ".venv\\Scripts\\python.exe"

if (!(Test-Path $python)) {
  Write-Host "未找到虚拟环境 Python: $python"
  Write-Host "请先在项目根目录执行：python -m venv .venv"
  exit 1
}

if (!(Test-Path $backendDir)) {
  Write-Host "未找到 backend 目录: $backendDir"
  exit 1
}

if (!(Test-Path $clientDir)) {
  Write-Host "未找到 client 目录: $clientDir"
  exit 1
}

Start-Process -WorkingDirectory $backendDir -FilePath $python -ArgumentList @(
  "-m", "uvicorn", "main:app",
  "--reload",
  "--host", "127.0.0.1",
  "--port", "8002"
)

Start-Process -WorkingDirectory $clientDir -FilePath "npm" -ArgumentList @("run", "dev")

Write-Host "Backend: http://127.0.0.1:8002"
Write-Host "Frontend: http://127.0.0.1:5173"

