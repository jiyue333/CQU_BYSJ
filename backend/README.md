# 人流计数与密度分析系统 - 后端

基于 FastAPI 的后端服务，提供视频流管理、推理结果推送等功能。

## 技术栈

- Python 3.11+
- FastAPI
- SQLAlchemy (async)
- PostgreSQL
- Redis
- YOLOv8n (Ultralytics)

## 项目结构

```
backend/
├── app/
│   ├── api/          # API 路由
│   ├── core/         # 核心配置（数据库、Redis、日志）
│   ├── models/       # SQLAlchemy 模型
│   ├── schemas/      # Pydantic Schema
│   ├── services/     # 业务服务
│   └── main.py       # 应用入口
├── tests/            # 测试
├── pyproject.toml    # 项目配置
└── .env.example      # 环境变量示例
```

## 开发

```bash
# 安装依赖
pip install -e ".[dev]"

# 复制环境变量
cp .env.example .env

# 运行开发服务器
uvicorn app.main:app --reload

# 运行测试
pytest
```

## API 文档

启动服务后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
