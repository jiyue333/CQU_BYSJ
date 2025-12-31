# 人流计数系统 - 后端服务 Dockerfile
# 基于 Python 3.11，包含 YOLO 推理依赖

# ============================================
# 阶段 1: 构建阶段
# ============================================
FROM python:3.11-slim AS builder

WORKDIR /app

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY pyproject.toml README.md ./

# 安装 Python 依赖到虚拟环境
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# ============================================
# 阶段 2: 运行阶段
# ============================================
FROM python:3.11-slim AS runtime

WORKDIR /app

# 安装运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 从构建阶段复制虚拟环境
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 复制应用代码
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY yolov8n.pt ./

# 创建非 root 用户
RUN useradd --create-home --shell /bin/bash appuser && \
    mkdir -p /data/uploads && \
    chown -R appuser:appuser /app /data

USER appuser

# 环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
