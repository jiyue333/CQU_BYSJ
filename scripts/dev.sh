#!/usr/bin/env bash
# CrowdFlow 本地开发 / Docker 启动脚本

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
BACKEND_VENV="$BACKEND_DIR/.venv"
LOG_DIR="$PROJECT_ROOT/log"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
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

log_step() {
    printf "%b\n" "${CYAN}[STEP]${NC} $1"
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

ensure_log_dir() {
    mkdir -p "$LOG_DIR"
}

rotate_log() {
    local logfile="$1"
    if [ -f "$logfile" ] && [ -s "$logfile" ]; then
        local ts
        ts="$(date '+%Y%m%d_%H%M%S')"
        mv "$logfile" "${logfile%.log}_${ts}.log"
    fi
}

# =========================================
# 进程清理：杀掉旧的前后端进程
# =========================================
kill_old_processes() {
    log_step "检查并清理旧进程..."
    local killed=0
    local pids=""

    # 杀掉旧的 uvicorn 后端进程
    pids="$(pgrep -f 'uvicorn app.main' 2>/dev/null || true)"
    if [ -n "$pids" ]; then
        log_warn "发现旧后端进程: ${pids}，正在终止..."
        echo "$pids" | xargs kill 2>/dev/null || true
        sleep 1
        echo "$pids" | xargs kill -9 2>/dev/null || true
        killed=1
    fi

    # 杀掉旧的 vite 前端进程
    pids="$(pgrep -f 'vite.*--port' 2>/dev/null || true)"
    if [ -n "$pids" ]; then
        log_warn "发现旧前端进程: ${pids}，正在终止..."
        echo "$pids" | xargs kill 2>/dev/null || true
        sleep 1
        echo "$pids" | xargs kill -9 2>/dev/null || true
        killed=1
    fi

    if [ "$killed" -eq 0 ]; then
        log_info "无旧进程需要清理"
    else
        log_info "旧进程已清理"
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

# =========================================
# 数据库检查与迁移
# =========================================
check_database() {
    log_step "检查数据库..."
    cd "$BACKEND_DIR"
    # shellcheck disable=SC1091
    source "$BACKEND_VENV/bin/activate"

    python -c "
from app.core.database import init_db
init_db()
print('[OK] 数据库初始化完成')
" 2>&1 | grep -v "^[0-9]\{4\}-\|^INFO\|^$" || true

    log_info "数据库就绪"
}

setup_local_env() {
    load_env
    ensure_backend_venv
    install_backend_deps
    install_frontend_deps
    check_database
    log_info "本地开发环境已就绪"
}

start_backend() {
    log_info "启动后端服务..."
    load_env
    ensure_log_dir
    kill_old_processes
    ensure_backend_venv
    install_backend_deps
    check_database

    rotate_log "$LOG_DIR/backend.log"
    log_info "后端日志: $LOG_DIR/backend.log"

    cd "$BACKEND_DIR"
    exec uvicorn app.main:app --reload --reload-exclude ".venv/*" --host "${HOST:-0.0.0.0}" --port "${PORT:-8000}" \
        2>&1 | tee "$LOG_DIR/backend.log"
}

start_frontend() {
    log_info "启动前端服务..."
    load_env
    ensure_log_dir
    kill_old_processes
    install_frontend_deps

    rotate_log "$LOG_DIR/frontend.log"
    log_info "前端日志: $LOG_DIR/frontend.log"

    cd "$FRONTEND_DIR"
    exec npm run dev -- --host "${FRONTEND_HOST:-0.0.0.0}" --port "${FRONTEND_PORT:-3000}" \
        2>&1 | tee "$LOG_DIR/frontend.log"
}

cleanup_services() {
    log_info "正在停止服务..."

    if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        kill "$BACKEND_PID" 2>/dev/null || true
        wait "$BACKEND_PID" 2>/dev/null || true
    fi

    if [ -n "$FRONTEND_PID" ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
        kill "$FRONTEND_PID" 2>/dev/null || true
        wait "$FRONTEND_PID" 2>/dev/null || true
    fi

    log_info "服务已停止"
}

wait_for_services() {
    while kill -0 "$BACKEND_PID" 2>/dev/null && kill -0 "$FRONTEND_PID" 2>/dev/null; do
        sleep 1
    done

    if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
        log_error "后端进程已退出，查看日志: $LOG_DIR/backend.log"
    fi

    if ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
        log_error "前端进程已退出，查看日志: $LOG_DIR/frontend.log"
    fi

    return 1
}

start_all() {
    log_info "==============================="
    log_info "  CrowdFlow 开发服务启动"
    log_info "==============================="

    load_env
    ensure_log_dir
    kill_old_processes

    log_step "准备环境..."
    ensure_backend_venv
    install_backend_deps
    install_frontend_deps

    check_database

    # 轮转旧日志
    rotate_log "$LOG_DIR/backend.log"
    rotate_log "$LOG_DIR/frontend.log"

    log_step "启动后端..."
    (
        cd "$BACKEND_DIR"
        # shellcheck disable=SC1091
        source "$BACKEND_VENV/bin/activate"
        exec uvicorn app.main:app --reload --reload-exclude ".venv/*" --host "${HOST:-0.0.0.0}" --port "${PORT:-8000}" \
            2>&1 | tee "$LOG_DIR/backend.log"
    ) &
    BACKEND_PID=$!

    log_step "启动前端..."
    (
        cd "$FRONTEND_DIR"
        exec npm run dev -- --host "${FRONTEND_HOST:-0.0.0.0}" --port "${FRONTEND_PORT:-3000}" \
            2>&1 | tee "$LOG_DIR/frontend.log"
    ) &
    FRONTEND_PID=$!

    # 等待服务就绪
    sleep 3

    echo ""
    log_info "==============================="
    log_info "  服务已启动"
    log_info "==============================="
    log_info "后端: http://localhost:${PORT:-8000}"
    log_info "前端: http://localhost:${FRONTEND_PORT:-3000}"
    log_info ""
    log_info "日志文件:"
    log_info "  后端: $LOG_DIR/backend.log"
    log_info "  前端: $LOG_DIR/frontend.log"
    log_info ""
    log_info "按 Ctrl+C 停止所有服务"
    echo ""

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
  stop        停止所有旧进程
  logs        实时查看日志
  docker-up   构建并后台启动 Docker 服务
  docker-down 停止 Docker 服务
  help        显示帮助

日志输出到 log/ 目录:
  log/backend.log    后端日志
  log/frontend.log   前端日志

常用环境变量（在项目根目录 .env 中配置）:
  HOST              后端监听地址，默认 0.0.0.0
  PORT              后端端口，默认 8000
  FRONTEND_HOST     前端监听地址，默认 0.0.0.0
  FRONTEND_PORT     前端端口，默认 3000
  YOLO_DEVICE       推理设备: cpu / cuda / mps
  DMCOUNT_INTERVAL_SEC  DM-Count 运行间隔（秒）
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
    stop)
        load_env
        kill_old_processes
        ;;
    logs)
        ensure_log_dir
        exec tail -f "$LOG_DIR/backend.log" "$LOG_DIR/frontend.log"
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
