#!/usr/bin/env bash
# OhMyDub 启动脚本 (Git Bash / WSL / Linux)
# Usage: ./start.sh [backend|frontend|all|full]

set -e
cd "$(dirname "$0")"

MODE="${1:-all}"

start_backend() {
    echo "[1/3] 启动后端..."
    title="OhMyDub-Backend"
    cmd=".venv/Scripts/uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --app-dir backend --reload"
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
        start "$title" cmd /c "$cmd"
    else
        "$SHELL" -c "$cmd" &
    fi
}

start_frontend() {
    echo "[2/3] 启动前端..."
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
        start "OhMyDub-Frontend" cmd /c "npm --prefix apps/web run dev"
    else
        (cd apps/web && npm run dev) &
    fi
}

start_gptsovits() {
    echo "[3/3] 启动 GPT-SoVITS API..."
    read -p "Enter GPT-SoVITS path [D:/GPT-SoVITS]: " gpt_path
    gpt_path="${gpt_path:-D:/GPT-SoVITS}"
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
        start "GPT-SoVITS" cmd /c "cd /d $gpt_path && .venv/Scripts/python api_v2.py -a 0.0.0.0:9880 -c GPT_SoVITS/configs/tts_infer.yaml"
    else
        (cd "$gpt_path" && .venv/bin/python api_v2.py -a 0.0.0.0:9880 -c GPT_SoVITS/configs/tts_infer.yaml) &
    fi
}

echo "============================================"
echo "  OhMyDub - 视频翻译配音系统"
echo "============================================"
echo ""

case "$MODE" in
    backend)
        start_backend
        ;;
    frontend)
        start_frontend
        ;;
    full)
        start_backend
        start_frontend
        start_gptsovits
        echo ""
        echo "后端:       http://localhost:8000"
        echo "前端:       http://localhost:3000"
        echo "API:        http://localhost:8000/docs"
        echo "GPT-SoVITS: http://localhost:9880"
        ;;
    all|*)
        start_backend
        start_frontend
        echo ""
        echo "后端: http://localhost:8000"
        echo "前端: http://localhost:3000"
        echo "API:  http://localhost:8000/docs"
        ;;
esac
