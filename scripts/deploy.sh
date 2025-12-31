#!/bin/bash
# 人流计数系统 - 一键部署脚本
# 
# 使用方法：
#   chmod +x scripts/deploy.sh
#   ./scripts/deploy.sh [dev|prod]

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印带颜色的消息
info() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# 检查 Docker 是否安装
check_docker() {
    if ! command -v docker &> /dev/null; then
        error "Docker 未安装，请先安装 Docker"
    fi
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        error "Docker Compose 未安装，请先安装 Docker Compose"
    fi
    info "Docker 环境检查通过"
}

# 检查并创建 .env 文件
check_env() {
    if [ ! -f .env ]; then
        warn ".env 文件不存在，从模板创建..."
        cp .env.example .env
        info ".env 文件已创建，请根据需要修改配置"
    else
        info ".env 文件已存在"
    fi
}

# 创建必要的目录
create_dirs() {
    info "创建必要的目录..."
    mkdir -p uploads zlm-logs zlm-media
    chmod 755 uploads zlm-logs zlm-media
}

# 开发模式部署
deploy_dev() {
    info "启动开发模式（仅基础设施服务）..."
    docker-compose up -d postgres redis zlmediakit
    
    info "等待服务启动..."
    sleep 5
    
    info "检查服务状态..."
    docker-compose ps
    
    echo ""
    info "开发模式启动完成！"
    echo ""
    echo "基础设施服务："
    echo "  - PostgreSQL: localhost:5432"
    echo "  - Redis: localhost:6379"
    echo "  - ZLMediaKit: localhost:8080"
    echo ""
    echo "请手动启动后端和前端："
    echo "  后端: cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
    echo "  前端: cd frontend && npm run dev"
}

# 生产模式部署
deploy_prod() {
    info "启动生产模式（所有服务容器化）..."
    
    # 使用 docker compose 或 docker-compose
    if docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    else
        COMPOSE_CMD="docker-compose"
    fi
    
    info "构建镜像..."
    $COMPOSE_CMD -f docker-compose.prod.yml build
    
    info "启动服务..."
    $COMPOSE_CMD -f docker-compose.prod.yml up -d
    
    info "等待服务启动..."
    sleep 15
    
    info "执行数据库迁移..."
    $COMPOSE_CMD -f docker-compose.prod.yml exec -T backend alembic upgrade head || warn "数据库迁移失败，可能需要手动执行"
    
    info "检查服务状态..."
    $COMPOSE_CMD -f docker-compose.prod.yml ps
    
    echo ""
    info "生产模式启动完成！"
    echo ""
    echo "服务架构："
    echo "  - frontend:  Vue 3 前端应用"
    echo "  - backend:   FastAPI API 服务"
    echo "  - inference: YOLO 推理服务（独立运行）"
    echo "  - postgres:  PostgreSQL 数据库"
    echo "  - redis:     Redis 消息队列"
    echo "  - zlmediakit: 流媒体网关"
    echo ""
    echo "访问地址："
    echo "  - 前端界面: http://localhost:3000"
    echo "  - 后端 API: http://localhost:8000"
    echo "  - API 文档: http://localhost:8000/docs"
    echo "  - ZLMediaKit: http://localhost:8080"
    echo ""
    echo "扩展推理服务："
    echo "  $COMPOSE_CMD -f docker-compose.prod.yml up -d --scale inference=3"
}

# 停止服务
stop_services() {
    info "停止所有服务..."
    if [ -f docker-compose.prod.yml ]; then
        docker-compose -f docker-compose.prod.yml down 2>/dev/null || true
    fi
    docker-compose down 2>/dev/null || true
    info "服务已停止"
}

# 显示帮助
show_help() {
    echo "人流计数系统 - 部署脚本"
    echo ""
    echo "用法: $0 [命令]"
    echo ""
    echo "命令:"
    echo "  dev     启动开发模式（仅基础设施服务）"
    echo "  prod    启动生产模式（所有服务容器化）"
    echo "  stop    停止所有服务"
    echo "  help    显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 dev   # 开发模式"
    echo "  $0 prod  # 生产模式"
}

# 主函数
main() {
    case "${1:-help}" in
        dev)
            check_docker
            check_env
            create_dirs
            deploy_dev
            ;;
        prod)
            check_docker
            check_env
            create_dirs
            deploy_prod
            ;;
        stop)
            stop_services
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            error "未知命令: $1\n使用 '$0 help' 查看帮助"
            ;;
    esac
}

main "$@"
