#!/bin/bash
# Docker 开发环境快速设置脚本

set -e

echo "=========================================="
echo "人流计数系统 - Docker 开发环境设置"
echo "=========================================="
echo ""

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "错误: Docker 未安装，请先安装 Docker"
    exit 1
fi

# 检查 Docker Compose 是否安装
if ! command -v docker-compose &> /dev/null; then
    echo "错误: Docker Compose 未安装，请先安装 Docker Compose"
    exit 1
fi

echo "✓ Docker 和 Docker Compose 已安装"
echo ""

# 检查 .env 文件是否存在
if [ ! -f .env ]; then
    echo "创建 .env 文件..."
    cp .env.example .env
    echo "✓ .env 文件已创建"
    echo ""
    echo "警告: 请编辑 .env 文件，修改以下配置："
    echo "  - POSTGRES_PASSWORD: PostgreSQL 密码"
    echo "  - ZLM_SECRET: ZLMediaKit API 密钥（必须修改）"
    echo ""
    echo "然后编辑 zlm-config/config.ini，确保 [api] secret 与 .env 中的 ZLM_SECRET 一致"
    echo ""
    read -p "按回车键继续..."
else
    echo "✓ .env 文件已存在"
fi

# 检查 ZLMediaKit 配置文件
if [ ! -f zlm-config/config.ini ]; then
    echo "错误: zlm-config/config.ini 不存在"
    exit 1
fi

echo "✓ ZLMediaKit 配置文件已存在"

# 检查 ZLM_SECRET 同步
if [ -f .env ]; then
    ENV_SECRET=$(grep "^ZLM_SECRET=" .env | cut -d'=' -f2)
    CONFIG_SECRET=$(grep "^secret=" zlm-config/config.ini | cut -d'=' -f2)
    
    if [ "$ENV_SECRET" != "$CONFIG_SECRET" ]; then
        echo ""
        echo "警告: ZLM_SECRET 不一致！"
        echo "  .env 中的值: $ENV_SECRET"
        echo "  config.ini 中的值: $CONFIG_SECRET"
        echo ""
        echo "请确保两个文件中的 secret 值一致："
        echo "  1. 编辑 .env 文件，修改 ZLM_SECRET"
        echo "  2. 编辑 zlm-config/config.ini，修改 [api] secret"
        echo ""
        read -p "是否继续启动？(y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        echo "✓ ZLM_SECRET 已同步"
    fi
fi

echo ""

# 创建必要的目录
echo "创建必要的目录..."
mkdir -p zlm-logs zlm-media uploads
echo "✓ 目录创建完成"
echo ""

# 启动服务
echo "启动 Docker 服务..."
docker-compose up -d

echo ""
echo "等待服务启动..."
sleep 5

# 检查服务状态
echo ""
echo "=========================================="
echo "服务状态"
echo "=========================================="
docker-compose ps

echo ""
echo "=========================================="
echo "设置完成！"
echo "=========================================="
echo ""
echo "后续步骤："
echo "1. 查看日志: docker-compose logs -f"
echo "2. 验证服务: 参考 README-DOCKER.md 中的测试清单"
echo "3. 停止服务: docker-compose down"
echo ""
echo "详细使用说明请查看 README-DOCKER.md"
