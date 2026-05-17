# OhMyDub 启动脚本 (PowerShell)
# 用法: .\start.ps1 [backend|frontend|all|full]

param(
    [ValidateSet("backend", "frontend", "all", "full")]
    [string]$Mode = "all"
)

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RootDir

function Start-Backend {
    Write-Host "[1/3] 启动后端..." -ForegroundColor Green
    $arg = ".venv\Scripts\uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --app-dir backend --reload"
    Start-Process -WindowStyle Normal -FilePath "cmd.exe" -ArgumentList "/c", $arg -WorkingDirectory $RootDir
}

function Start-Frontend {
    Write-Host "[2/3] 启动前端..." -ForegroundColor Green
    Start-Process -WindowStyle Normal -FilePath "cmd.exe" -ArgumentList "/c", "npm --prefix apps/web run dev" -WorkingDirectory $RootDir
}

function Start-GPTSoVITS {
    Write-Host "[3/3] 启动 GPT-SoVITS API..." -ForegroundColor Green
    $defaultPath = "D:\GPT-SoVITS"
    $gptPath = Read-Host "请输入 GPT-SoVITS 目录路径 (直接回车使用默认: $defaultPath)"
    if ([string]::IsNullOrWhiteSpace($gptPath)) { $gptPath = $defaultPath }
    $arg = ".venv\Scripts\python api_v2.py -a 0.0.0.0:9880 -c GPT_SoVITS/configs/tts_infer.yaml"
    Start-Process -WindowStyle Normal -FilePath "cmd.exe" -ArgumentList "/c", $arg -WorkingDirectory $gptPath
}

switch ($Mode) {
    "backend" {
        Start-Backend
    }
    "frontend" {
        Start-Frontend
    }
    "all" {
        Start-Backend
        Start-Frontend
        Write-Host "`n后端: http://localhost:8000" -ForegroundColor Cyan
        Write-Host "前端: http://localhost:3000" -ForegroundColor Cyan
        Write-Host "API:  http://localhost:8000/docs" -ForegroundColor Cyan
    }
    "full" {
        Start-Backend
        Start-Frontend
        Start-GPTSoVITS
        Write-Host "`n后端:       http://localhost:8000" -ForegroundColor Cyan
        Write-Host "前端:       http://localhost:3000" -ForegroundColor Cyan
        Write-Host "API:        http://localhost:8000/docs" -ForegroundColor Cyan
        Write-Host "GPT-SoVITS: http://localhost:9880" -ForegroundColor Cyan
    }
}
