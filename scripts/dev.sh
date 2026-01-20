#!/bin/bash
# 开发模式启动脚本

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 加载 .env 配置
load_env() {
    if [ -f "$PROJECT_ROOT/.env" ]; then
        export $(grep -v '^#' "$PROJECT_ROOT/.env" | xargs)
    fi
}

# 激活 Python 环境
activate_python_env() {
    local env_type="${PYTHON_ENV:-venv}"
    local conda_name="${CONDA_ENV_NAME:-crowdflow}"

    if [ "$env_type" = "conda" ]; then
        log_info "激活 conda 环境: $conda_name"

        # 初始化 conda（兼容不同 shell）
        if [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
            source "$HOME/miniconda3/etc/profile.d/conda.sh"
        elif [ -f "$HOME/anaconda3/etc/profile.d/conda.sh" ]; then
            source "$HOME/anaconda3/etc/profile.d/conda.sh"
        elif [ -f "/opt/homebrew/Caskroom/miniconda/base/etc/profile.d/conda.sh" ]; then
            source "/opt/homebrew/Caskroom/miniconda/base/etc/profile.d/conda.sh"
        else
            # 尝试使用 conda 命令
            eval "$(conda shell.bash hook 2>/dev/null)" || {
                log_error "无法初始化 conda，请检查 conda 安装"
                exit 1
            }
        fi

        # 检查环境是否存在
        if ! conda env list | grep -q "^$conda_name "; then
            log_warn "conda 环境 '$conda_name' 不存在，正在创建..."
            conda create -n "$conda_name" python=3.11 -y
        fi

        conda activate "$conda_name"
    else
        log_info "激活 venv 环境"
        cd "$PROJECT_ROOT/backend"

        if [ ! -d ".venv" ]; then
            log_warn "venv 不存在，正在创建..."
            python3 -m venv .venv
        fi

        source .venv/bin/activate
    fi
}

# 安装后端依赖
install_backend_deps() {
    cd "$PROJECT_ROOT/backend"

    # 检查是否已安装
    if ! python -c "import fastapi" 2>/dev/null; then
        log_info "安装后端依赖..."
        pip install -e ".[dev]"
    fi
}

# 启动后端
start_backend() {
    log_info "启动后端服务..."

    load_env
    activate_python_env
    install_backend_deps

    cd "$PROJECT_ROOT/backend"
    uvicorn app.main:app --reload --host 0.0.0.0 --port "${PORT:-8000}"
}

# 获取前端包管理器
get_pkg_manager() {
    if command -v pnpm &> /dev/null; then
        echo "pnpm"
    elif command -v yarn &> /dev/null; then
        echo "yarn"
    else
        echo "npm"
    fi
}

# 启动前端
start_frontend() {
    log_info "启动前端服务..."
    cd "$PROJECT_ROOT/frontend"

    local pkg_manager=$(get_pkg_manager)
    log_info "使用包管理器: $pkg_manager"

    if [ ! -d "node_modules" ]; then
        log_warn "依赖未安装，正在安装..."
        $pkg_manager install
    fi

    $pkg_manager run dev
}

# 同时启动前后端
start_all() {
    log_info "同时启动前后端服务..."

    load_env
    activate_python_env
    install_backend_deps

    # 后台启动后端
    cd "$PROJECT_ROOT/backend"
    uvicorn app.main:app --reload --host 0.0.0.0 --port "${PORT:-8000}" &
    BACKEND_PID=$!

    # 启动前端
    cd "$PROJECT_ROOT/frontend"
    local pkg_manager=$(get_pkg_manager)
    if [ ! -d "node_modules" ]; then
        $pkg_manager install
    fi
    $pkg_manager run dev &
    FRONTEND_PID=$!

    log_info "后端 PID: $BACKEND_PID"
    log_info "前端 PID: $FRONTEND_PID"
    log_info "按 Ctrl+C 停止所有服务"

    trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" SIGINT SIGTERM
    wait
}

# 显示帮助
show_help() {
    echo "用法: $0 [命令]"
    echo ""
    echo "命令:"
    echo "  backend    仅启动后端"
    echo "  frontend   仅启动前端"
    echo "  all        启动全部（默认）"
    echo ""
    echo "环境变量（在 .env 中配置）:"
    echo "  PYTHON_ENV      Python 环境类型: conda / venv（默认 venv）"
    echo "  CONDA_ENV_NAME  conda 环境名称（默认 crowdflow）"
}

# 主入口
case "${1:-all}" in
    backend)
        start_backend
        ;;
    frontend)
        start_frontend
        ;;
    all)
        start_all
        ;;
    help|-h|--help)
        show_help
        ;;
    *)
        log_error "未知命令: $1"
        show_help
        exit 1
        ;;
esac
