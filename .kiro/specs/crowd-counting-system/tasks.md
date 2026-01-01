# 实现计划：人流计数与密度分析系统

## 概述

基于 YOLO 的实时人流计数与密度分析系统实现计划。采用播放帧率与推理频率解耦的设计，后端使用 FastAPI + Redis，前端使用 Vue 3，媒体网关使用 ZLMediaKit。

## 技术栈

- **后端**: Python 3.11+, FastAPI, Redis, PostgreSQL
- **前端**: Vue 3, TypeScript, flv.js, hls.js, Canvas API
- **推理**: YOLOv8n (Ultralytics)
- **媒体网关**: ZLMediaKit
- **测试**: pytest, pytest-asyncio, hypothesis (属性测试)

## 任务列表

- [x] 1. 项目初始化与基础设施
  - [x] 1.1 创建后端项目结构
    - 初始化 FastAPI 项目
    - 配置 pyproject.toml 依赖管理
    - 设置项目目录结构 (api/, services/, models/, core/)
    - _Requirements: 7.2_

  - [x] 1.2 创建前端项目结构
    - 使用 Vite 初始化 Vue 3 + TypeScript 项目
    - 配置 ESLint, Prettier
    - 设置项目目录结构 (components/, views/, stores/, api/)
    - _Requirements: 7.2_

  - [x] 1.3 配置数据库与 Redis
    - 配置 PostgreSQL 连接 (SQLAlchemy async)
    - 配置 Redis 连接 (redis-py async)
    - 创建数据库迁移脚本 (Alembic)
    - _Requirements: 6.1, 8.4_

  - [x] 1.4 配置 Docker Compose 开发环境
    - PostgreSQL 容器
    - Redis 容器
    - ZLMediaKit 容器（端口：1935/8080/8554/10000/8000udp）
    - 配置文件挂载（zlm-config, zlm-logs, zlm-media）
    - 环境变量配置（ZLM_SECRET）
    - _Requirements: 7.2_

- [x] 2. 核心数据模型实现
  - [x] 2.1 实现 VideoStream 模型
    - 定义 StreamType 枚举 (file/webcam/rtsp)
    - 定义 StreamStatus 枚举 (starting/running/stopped/error/cooldown)
    - 实现 VideoStream SQLAlchemy 模型
    - 实现 Pydantic schemas
    - _Requirements: 1.4, 9.4_

  - [x] 2.2 编写 VideoStream 属性测试
    - **Property 8: 流状态一致性**
    - **Validates: Requirements 9.4**

  - [x] 2.3 实现 ROI 模型
    - 定义 Point, DensityThresholds 模型
    - 实现 ROI SQLAlchemy 模型
    - 实现 Pydantic schemas
    - _Requirements: 3.1, 3.2_

  - [x] 2.4 编写 ROI 属性测试
    - **Property 4: ROI配置持久化**
    - **Validates: Requirements 3.1**

  - [x] 2.5 实现 DetectionResult 模型
    - 定义 Detection, RegionStat, DensityLevel 模型
    - 实现 DetectionResult Pydantic schema
    - _Requirements: 2.3, 3.3, 3.4_

  - [x] 2.6 实现 SystemConfig 模型
    - 定义配置字段 (confidence_threshold, inference_fps, heatmap_grid_size)
    - 实现 SQLAlchemy 模型和 Pydantic schemas
    - _Requirements: 8.1, 8.2, 8.3_

  - [x] 2.7 编写 SystemConfig 属性测试
    - **Property 7: 配置范围约束**
    - **Validates: Requirements 8.3, 8.4**

  - [x] 2.8 实现 HistoryStat 模型
    - 定义历史统计 SQLAlchemy 模型
    - 实现 Pydantic schemas
    - _Requirements: 6.1_

- [x] 3. Checkpoint - 数据模型验证
  - 确保所有模型测试通过
  - 确保数据库迁移正常运行
  - 如有问题请询问用户

- [x] 4. Stream Manager 控制面后端
  - [x] 4.1 实现流管理 REST API
    - POST /api/streams - 创建视频流（含并发限制检查）
    - GET /api/streams - 获取所有视频流列表
    - GET /api/streams/{stream_id} - 获取流状态和 play_url
    - GET /api/streams/{stream_id}/latest-result - 获取最新检测结果
    - POST /api/streams/{stream_id}/start - 开始播放
    - POST /api/streams/{stream_id}/stop - 停止播放
    - DELETE /api/streams/{stream_id} - 删除视频流
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [x] 4.2 编写流管理 API 属性测试
    - **Property 1: 视频源统一抽象**
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.4**

  - [x] 4.3 实现流生命周期管理服务
    - 实现 StreamService 类
    - 状态转换逻辑 (starting → running/error, running → stopped/error)
    - 与媒体网关交互逻辑
    - _Requirements: 1.5, 9.4_

  - [x] 4.4 实现 WebSocket 结果推送服务
    - 实现 ResultPushService 类
    - WebSocket 端点 /ws/result/{stream_id}
    - Redis Streams 消费与转发（XREAD 阻塞读取）
    - WebSocket 断点续传（XRANGE 恢复遗漏消息）
    - _Requirements: 5.1, 5.2, 5.3_

  - [x] 4.5 实现 WebSocket 状态推送服务
    - WebSocket 端点 /ws/status
    - 流状态变更通知
    - _Requirements: 9.4_

  - [x] 4.6 实现推理服务控制接口
    - Redis PubSub 发布 START/STOP 指令到 inference:control 通道（即时指令，不需持久化）
    - Redis Streams 消费推理状态上报（inference:status Stream）
    - 指令格式：{cmd_id, stream_id, action, fps, timestamp}
    - 幂等性保证：重复 START 忽略，重复 STOP 安全
    - _Requirements: 2.1_

- [x] 5. 媒体网关集成
  - [x] 5.1 配置 ZLMediaKit 媒体网关
    - 配置 RTSP 拉流（addStreamProxy）
    - 配置 WebRTC/HLS/HTTP-FLV 播放输出
    - 配置快照 API（getSnap）
    - 配置 API 密钥（secret）
    - _Requirements: 1.1, 1.2, 1.3_

  - [x] 5.2 实现 GatewayAdapter 适配层
    - 实现 GatewayAdapter 抽象接口
    - 实现 ZLMediaKitAdapter 具体实现
    - create_rtsp_proxy（调用 addStreamProxy）
    - create_file_stream（调用 addFFmpegSource）
    - get_snapshot（调用 getSnap）
    - delete_stream（调用 delStreamProxy）
    - _Requirements: 1.4, 2.1_

  - [x] 5.3 实现文件上传与转流
    - 文件上传 API（支持 mp4/avi/mkv/mov/webm/flv）
    - 文件大小限制（500MB）
    - 文件存储服务
    - 通知网关转流（addFFmpegSource）
    - _Requirements: 1.1_

- [x] 6. Checkpoint - 后端核心功能验证
  - 确保流管理 API 正常工作
  - 确保 WebSocket 连接稳定
  - 确保媒体网关集成正常
  - 如有问题请询问用户

- [x] 7. 推理服务实现
  - [x] 7.1 实现 YOLO 模型加载与推理
    - 加载 YOLOv8n 预训练模型
    - 实现推理方法 (输入 JPEG bytes, 输出检测结果)
    - 置信度过滤
    - _Requirements: 2.2, 2.4_

  - [x] 7.2 编写置信度过滤属性测试
    - **Property 2: 置信度过滤**
    - **Validates: Requirements 2.4, 8.1**

  - [x] 7.3 实现推理循环 Worker
    - 实现 InferenceWorker 类
    - 订阅 Redis PubSub inference:control 通道接收 START/STOP 指令
    - 按频率调用 getSnap 抓帧
    - 只保最新帧，忙就丢
    - _Requirements: 2.1, 2.2_

  - [x] 7.4 实现检测结果统计
    - 总人数统计
    - 区域密度计算（Shoelace 公式计算面积 + 射线法判断点在多边形内）
    - 密度等级分类 (LOW/MEDIUM/HIGH)
    - _Requirements: 2.3, 3.3, 3.4_

  - [x] 7.5 编写密度计算属性测试
    - **Property 3: 密度计算与等级分类**
    - **Validates: Requirements 3.3, 3.4**

  - [x] 7.6 实现热力图数据生成
    - 根据检测位置生成热力图网格（默认 20x20）
    - 实现 EMA 平滑算法：EMA_t = α * value_t + (1-α) * EMA_{t-1}，α=0.3
    - 初始值处理：第一帧直接使用原始值
    - _Requirements: 4.1_

  - [x] 7.7 编写热力图生成属性测试
    - **Property 5: 热力图生成**
    - **Validates: Requirements 4.1**

  - [x] 7.8 实现结果发布到 Redis Streams
    - 写入 result:{stream_id} Stream（XADD）
    - 配置 MAXLEN=100 实现自动背压
    - 状态上报写入 inference:status Stream
    - _Requirements: 5.3_

- [x] 8. Checkpoint - 推理服务验证
  - 确保推理服务正常启动
  - 确保检测结果正确发布
  - 如有问题请询问用户

- [x] 9. 前端核心组件实现
  - [x] 9.1 实现视频源选择组件 (VideoSourceSelector)
    - 本地视频文件选择与上传
    - 浏览器摄像头授权
    - RTSP 地址输入
    - _Requirements: 1.1, 1.2, 1.3, 1.5_

  - [x] 9.2 实现视频播放器组件 (VideoPlayer)
    - 协议优先级：WebRTC → HTTP-FLV → HLS
    - WebRTC 播放支持（最低延迟）
    - HTTP-FLV 播放支持（flv.js）
    - HLS 播放支持（hls.js，降级方案）
    - 自动协议降级逻辑
    - _Requirements: 1.1, 1.2, 1.3_

  - [x] 9.3 实现热力图叠加组件 (HeatmapOverlay)
    - Canvas 叠加层
    - EMA 平滑过渡效果（alpha=0.3）
    - 显示/隐藏开关
    - _Requirements: 4.2, 4.3, 4.4, 4.5_

  - [x] 9.4 实现 WebSocket 服务
    - 连接管理
    - 自动重连（指数退避：1s → 2s → 4s → ... → 30s max）
    - 重连后状态恢复（重新订阅 + 获取最新数据）
    - 结果订阅
    - _Requirements: 5.3, 9.1_

  - [x] 9.5 实现 API 服务层
    - 流管理 API 封装
    - 错误处理
    - _Requirements: 1.5, 1.6_

- [x] 10. ROI 区域管理
  - [x] 10.1 实现 ROI 管理 REST API
    - POST /api/streams/{stream_id}/rois - 创建 ROI
    - GET /api/streams/{stream_id}/rois - 获取 ROI 列表
    - PUT /api/streams/{stream_id}/rois/{roi_id} - 更新 ROI
    - DELETE /api/streams/{stream_id}/rois/{roi_id} - 删除 ROI
    - _Requirements: 3.1, 3.2, 3.5_

  - [x] 10.2 实现 ROI 绘制组件 (ROIDrawer)
    - Canvas 多边形绘制
    - 编辑与删除功能
    - 区域命名
    - _Requirements: 3.1, 3.2_

  - [x] 10.3 实现区域密度显示组件
    - 显示每个区域的密度值
    - 密度等级颜色标识
    - _Requirements: 3.3, 3.4, 5.2_

- [x] 11. 实时数据展示
  - [x] 11.1 实现实时统计面板组件 (StatsPanel)
    - 当前总人数显示
    - 各区域密度显示
    - 数据更新动画
    - _Requirements: 5.1, 5.2, 5.3_

  - [x] 11.2 实现多路视频管理界面
    - 视频流列表
    - 添加/删除视频流
    - 状态指示器
    - _Requirements: 7.1, 9.4_

- [x] 12. Checkpoint - 前端核心功能验证
  - 确保视频播放正常
  - 确保热力图叠加正常
  - 确保实时数据更新正常
  - 如有问题请询问用户

- [x] 13. 历史数据功能
  - [x] 13.1 实现历史数据存储服务
    - 定时保存检测统计数据
    - 数据聚合 (分钟/小时/天)
    - _Requirements: 6.1_

  - [x] 13.2 实现历史数据查询 API
    - GET /api/streams/{stream_id}/history - 查询历史数据
    - 支持时间范围过滤
    - 支持聚合粒度选择
    - _Requirements: 6.2_

  - [x] 13.3 编写历史数据查询属性测试
    - **Property 6: 历史数据时间范围查询**
    - **Validates: Requirements 6.1, 6.2**

  - [x] 13.4 实现历史数据图表组件
    - 折线图 (人数趋势)
    - 柱状图 (区域密度对比)
    - 时间范围选择器
    - _Requirements: 6.3_

  - [x] 13.5 实现数据导出功能
    - CSV 导出
    - Excel 导出
    - _Requirements: 6.4_

- [x] 14. 配置管理
  - [x] 14.1 实现配置管理 API
    - GET /api/config/{stream_id} - 获取配置
    - PUT /api/config/{stream_id} - 更新配置
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

  - [x] 14.2 实现配置管理界面
    - 置信度阈值配置
    - 密度等级阈值配置
    - 推理频率配置
    - _Requirements: 8.1, 8.2, 8.3_

- [x] 15. 错误处理与稳定性
  - [x] 15.1 实现视频流重连机制
    - 自动重连逻辑
    - 指数退避策略（1s → 2s → 4s → ... → 30s max）
    - 重连次数限制（5 次）
    - Cooldown 状态管理
    - COOLDOWN 自动恢复（60 秒后自动重试 START）
    - _Requirements: 9.1, 9.2_

  - [x] 15.2 实现错误通知与状态指示
    - 前端错误提示组件
    - 连接状态指示器
    - 处理状态指示器
    - _Requirements: 9.2, 9.4_

  - [x] 15.3 实现日志记录
    - 后端结构化日志
    - 错误日志记录
    - _Requirements: 9.3_

- [x] 16. Checkpoint - 完整功能验证
  - 确保所有功能正常工作
  - 确保错误处理正常
  - 如有问题请询问用户

- [x] 17. 集成测试
  - [x] 17.1 编写端到端测试
    - 完整视频流处理链路测试
    - WebSocket 连接与消息推送测试
    - _Requirements: 7.1, 7.2_

  - [x] 17.2 编写多路视频并发测试
    - 多路视频同时处理测试
    - 资源使用监控
    - _Requirements: 7.1_

- [x] 18. 最终 Checkpoint
  - 确保所有测试通过
  - 确保系统稳定运行
  - 如有问题请询问用户

## 备注

- 所有任务均为必须完成的任务
- 每个任务引用具体的需求编号以便追溯
- Checkpoint 任务用于阶段性验证，确保增量开发质量
- 属性测试验证系统的正确性属性，确保核心逻辑正确
