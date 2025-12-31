# 人流计数与密度分析系统 - 前端

基于 Vue 3 + TypeScript + Vite 的实时人流计数与密度分析系统前端应用。

## 技术栈

- **框架**: Vue 3 (Composition API)
- **语言**: TypeScript
- **构建工具**: Vite
- **代码规范**: ESLint + Prettier

## 项目结构

```
frontend/
├── src/
│   ├── api/          # API 客户端模块
│   ├── assets/       # 静态资源
│   ├── components/   # 可复用组件
│   ├── stores/       # 状态管理
│   ├── views/        # 页面级组件
│   ├── App.vue       # 根组件
│   └── main.ts       # 应用入口
├── public/           # 公共静态资源
└── index.html        # HTML 模板
```

## 开发指南

### 安装依赖

```bash
npm install
```

### 启动开发服务器

```bash
npm run dev
```

### 构建生产版本

```bash
npm run build
```

### 预览生产构建

```bash
npm run preview
```

### 代码检查

```bash
# 运行 ESLint
npm run lint

# 自动修复 ESLint 问题
npm run lint:fix

# 格式化代码
npm run format
```

## 核心功能模块

### 1. 视频播放器 (components/)
- 支持 WebRTC/HTTP-FLV/HLS 多协议播放
- 自动协议降级
- 热力图叠加层

### 2. ROI 区域管理 (components/)
- Canvas 多边形绘制
- 区域编辑与删除
- 密度可视化

### 3. 实时数据展示 (components/)
- WebSocket 实时数据推送
- 统计面板
- 多路视频管理

### 4. 历史数据查询 (views/)
- 时间范围查询
- 图表可视化
- 数据导出

### 5. 配置管理 (views/)
- 系统参数配置
- 密度阈值设置
- 推理频率调整

## 开发规范

### 组件命名
- 使用 PascalCase 命名组件文件
- 组件名应具有描述性

### 代码风格
- 使用 Composition API
- 使用 `<script setup>` 语法
- 遵循 ESLint 和 Prettier 规则

### 类型定义
- 为所有 API 响应定义 TypeScript 接口
- 使用类型推断减少冗余类型标注

## 环境变量

创建 `.env.local` 文件配置环境变量：

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=ws://localhost:8000
```

## 浏览器支持

- Chrome >= 90
- Firefox >= 88
- Safari >= 14
- Edge >= 90
