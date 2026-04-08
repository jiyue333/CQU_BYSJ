#!/usr/bin/env bash
# CrowdFlow 本地开发 / Docker 启动脚本

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
BACKEND_VENV="$BACKEND_DIR/.venv"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

BACKEND_PID=""
FRONTEND_PID=""

log_info() {
    printf "%b\n" "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    printf "%b\n" "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    printf "%b\n" "${RED}[ERROR]${NC} $1"
}

require_command() {
    if ! command -v "$1" >/dev/null 2>&1; then
        log_error "缺少命令: $1"
        exit 1
    fi
}

load_env() {
    if [ -f "$PROJECT_ROOT/.env" ]; then
        set -a
        # shellcheck disable=SC1091
        source "$PROJECT_ROOT/.env"
        set +a
    else
        log_warn "未找到 .env，使用默认配置"
    fi
}

ensure_backend_venv() {
    require_command python3

    if [ ! -d "$BACKEND_VENV" ]; then
        log_info "创建后端虚拟环境: $BACKEND_VENV"
        python3 -m venv "$BACKEND_VENV"
    fi

    # shellcheck disable=SC1091
    source "$BACKEND_VENV/bin/activate"
}

ensure_backend_build_tools() {
    if ! python -c "import setuptools, wheel" >/dev/null 2>&1; then
        log_info "安装 Python 打包工具..."
        python -m pip install setuptools wheel
    fi
}

install_backend_deps() {
    local stamp_file="$BACKEND_VENV/.deps-installed"

    cd "$BACKEND_DIR"
    ensure_backend_build_tools

    if [ ! -f "$stamp_file" ] || [ "pyproject.toml" -nt "$stamp_file" ]; then
        log_info "安装后端依赖..."
        python -m pip install --no-build-isolation -e ".[dev]"
        touch "$stamp_file"
    fi
}

install_frontend_deps() {
    local stamp_file="$FRONTEND_DIR/node_modules/.deps-installed"

    require_command npm
    cd "$FRONTEND_DIR"

    if [ ! -d "node_modules" ] || [ ! -f "$stamp_file" ] || [ "package.json" -nt "$stamp_file" ] || [ "package-lock.json" -nt "$stamp_file" ]; then
        log_info "安装前端依赖..."
        npm install
        mkdir -p node_modules
        touch "$stamp_file"
    fi
}

setup_local_env() {
    load_env
    ensure_backend_venv
    install_backend_deps
    install_frontend_deps
    log_info "本地开发环境已就绪"
}

start_backend() {
    log_info "启动后端服务..."
    load_env
    ensure_backend_venv
    install_backend_deps

    cd "$BACKEND_DIR"
    exec uvicorn app.main:app --reload --reload-exclude ".venv/*" --host "${HOST:-0.0.0.0}" --port "${PORT:-8000}"
}

start_frontend() {
    log_info "启动前端服务..."
    load_env
    install_frontend_deps

    cd "$FRONTEND_DIR"
    exec npm run dev -- --host "${FRONTEND_HOST:-0.0.0.0}" --port "${FRONTEND_PORT:-3000}"
}

cleanup_services() {
    if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        kill "$BACKEND_PID" 2>/dev/null || true
        wait "$BACKEND_PID" 2>/dev/null || true
    fi

    if [ -n "$FRONTEND_PID" ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
        kill "$FRONTEND_PID" 2>/dev/null || true
        wait "$FRONTEND_PID" 2>/dev/null || true
    fi
}

wait_for_services() {
    while kill -0 "$BACKEND_PID" 2>/dev/null && kill -0 "$FRONTEND_PID" 2>/dev/null; do
        sleep 1
    done

    if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
        log_error "后端进程已退出"
    fi

    if ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
        log_error "前端进程已退出"
    fi

    return 1
}

start_all() {
    log_info "同时启动前后端服务..."
    load_env
    ensure_backend_venv
    install_backend_deps
    install_frontend_deps

    (
        cd "$BACKEND_DIR"
        # shellcheck disable=SC1091
        source "$BACKEND_VENV/bin/activate"
        exec uvicorn app.main:app --reload --reload-exclude ".venv/*" --host "${HOST:-0.0.0.0}" --port "${PORT:-8000}"
    ) &
    BACKEND_PID=$!

    (
        cd "$FRONTEND_DIR"
        exec npm run dev -- --host "${FRONTEND_HOST:-0.0.0.0}" --port "${FRONTEND_PORT:-3000}"
    ) &
    FRONTEND_PID=$!

    log_info "后端: http://localhost:${PORT:-8000}"
    log_info "前端: http://localhost:${FRONTEND_PORT:-3000}"
    log_info "按 Ctrl+C 停止所有服务"

    trap 'cleanup_services; exit 0' INT TERM

    local status=0
    wait_for_services || status=$?
    cleanup_services
    return "$status"
}

docker_compose() {
    if docker compose version >/dev/null 2>&1; then
        docker compose "$@"
    elif command -v docker-compose >/dev/null 2>&1; then
        docker-compose "$@"
    else
        log_error "未找到 docker compose 或 docker-compose"
        exit 1
    fi
}

docker_up() {
    log_info "构建并启动 Docker 服务..."
    load_env
    docker_compose up --build -d
    log_info "后端: http://localhost:${BACKEND_PORT:-8000}"
    log_info "前端: http://localhost:${FRONTEND_PORT:-3000}"
}

docker_down() {
    log_info "停止 Docker 服务..."
    docker_compose down
}

show_help() {
    cat <<'EOF'
用法: ./scripts/dev.sh [命令]

命令:
  all         启动前后端（默认）
  setup       创建 backend/.venv 并安装前后端依赖
  backend     仅启动后端
  frontend    仅启动前端
  docker-up   构建并后台启动 Docker 服务
  docker-down 停止 Docker 服务
  help        显示帮助

常用环境变量（在项目根目录 .env 中配置）:
  HOST            后端监听地址，默认 0.0.0.0
  PORT            后端端口，默认 8000
  FRONTEND_HOST   前端监听地址，默认 0.0.0.0
  FRONTEND_PORT   前端端口，默认 3000
EOF
}

case "${1:-all}" in
    all)
        start_all
        ;;
    setup)
        setup_local_env
        ;;
    backend)
        start_backend
        ;;
    frontend)
        start_frontend
        ;;
    docker-up)
        docker_up
        ;;
    docker-down)
        docker_down
        ;;
    help|-h|--help)
        show_help
        ;;
    *)
        log_error "未知命令: ${1}"
        show_help
        exit 1
        ;;
esac
