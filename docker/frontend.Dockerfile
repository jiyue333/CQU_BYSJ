# 前端 Dockerfile
FROM node:18-alpine AS builder

WORKDIR /app

ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=${VITE_API_URL}

# 复制依赖文件
COPY frontend/package.json frontend/package-lock.json ./

# 安装依赖
RUN npm install

# 复制源代码
COPY frontend/ .

# 构建（生产模式）
RUN npm exec vite build

# 生产镜像 - 使用轻量 HTTP 服务器
FROM node:18-alpine

WORKDIR /app

RUN npm install -g serve

COPY --from=builder /app/dist ./dist

EXPOSE 3000

CMD ["serve", "-s", "dist", "-l", "3000"]
