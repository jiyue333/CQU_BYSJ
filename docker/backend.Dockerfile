# 后端 Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖（OpenCV 需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制后端代码和默认模型
COPY backend/ ./
COPY yolo11n.pt ./yolo11n.pt

# 安装 Python 依赖
RUN pip install --no-cache-dir setuptools wheel && \
    pip install --no-cache-dir --no-build-isolation -e .

# 创建数据目录
RUN mkdir -p /data /uploads /models /logs

# 环境变量
ENV HOST=0.0.0.0
ENV PORT=8000
ENV DATA_DIR=/data
ENV UPLOAD_DIR=/uploads/videos
ENV MODEL_DIR=/models
ENV LOGS_DIR=/logs
ENV YOLO_MODEL_PATH=/app/yolo11n.pt

EXPOSE 8000

CMD ["python", "-m", "app.main"]
