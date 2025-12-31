# 前端服务

基于 Vue 3 + TypeScript + Vite 的前端应用。

## 快速开始

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build
```

## 开发命令

```bash
npm run dev      # 启动开发服务器
npm run build    # 构建生产版本
npm run preview  # 预览生产构建
npm run lint     # 代码检查
npm run format   # 代码格式化
```

## 环境变量

创建 `.env.local` 文件：

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=ws://localhost:8000
```

## 技术栈

- Vue 3 (Composition API)
- TypeScript
- Vite
- ESLint + Prettier
