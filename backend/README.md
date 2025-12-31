# 后端服务

基于 FastAPI 的后端服务。

## 快速开始

```bash
# 1. 安装依赖
pip install -e ".[dev]"

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件

# 3. 启动依赖服务（使用 Docker Compose）
cd ..
docker-compose up -d postgres redis

# 4. 初始化数据库
alembic upgrade head

# 5. 启动服务
uvicorn app.main:app --reload
```

## 开发命令

```bash
# 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 运行测试
pytest

# 代码检查
ruff check .
ruff format .
```

## 数据库迁移

```bash
# 生成迁移
alembic revision --autogenerate -m "描述"

# 执行迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1

# 查看历史
alembic history
```

## API 文档

启动服务后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 技术栈

- Python 3.11+
- FastAPI
- SQLAlchemy (async)
- PostgreSQL
- Redis
- YOLOv8n
