@echo off
chcp 65001 >nul
cd /d "%~dp0"

title OhMyDub Launcher

echo ============================================
echo   OhMyDub - Video Dubbing System
echo ============================================
echo.
echo Select mode:
echo   1 - Backend only
echo   2 - Frontend only
echo   3 - Backend + Frontend (recommended)
echo   4 - All (Backend + Frontend + GPT-SoVITS)
echo   0 - Exit
echo.

set /p mode="Enter number (0-4): "

if "%mode%"=="0" exit /b
if "%mode%"=="1" goto backend
if "%mode%"=="2" goto frontend
if "%mode%"=="3" goto both
if "%mode%"=="4" goto all

echo Invalid input.
exit /b

:backend
echo.
echo [1/3] Starting backend...
start "OhMyDub Backend" cmd /c ".venv\Scripts\uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir backend --reload"
exit /b

:frontend
echo.
echo [2/3] Starting frontend...
start "OhMyDub Frontend" cmd /c "npm --prefix apps/web run dev"
exit /b

:both
echo.
echo [1/3] Starting backend...
start "OhMyDub Backend" cmd /c ".venv\Scripts\uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir backend --reload"
echo [2/3] Starting frontend...
start "OhMyDub Frontend" cmd /c "npm --prefix apps/web run dev"
echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
echo API:      http://localhost:8000/docs
exit /b

:all
echo.
echo [1/3] Starting backend...
start "OhMyDub Backend" cmd /c ".venv\Scripts\uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir backend --reload"
echo [2/3] Starting frontend...
start "OhMyDub Frontend" cmd /c "npm --prefix apps/web run dev"
echo [3/3] Starting GPT-SoVITS API...
set /p gpt_path="Enter GPT-SoVITS path (default: D:\GPT-SoVITS): "
if "%gpt_path%"=="" set "gpt_path=D:\GPT-SoVITS"
start "GPT-SoVITS" cmd /c "cd /d %gpt_path% && .venv\Scripts\python api_v2.py -a 0.0.0.0:9880 -c GPT_SoVITS/configs/tts_infer.yaml"
echo.
echo Backend:       http://localhost:8000
echo Frontend:      http://localhost:3000
echo API:           http://localhost:8000/docs
echo GPT-SoVITS:    http://localhost:9880
exit /b
