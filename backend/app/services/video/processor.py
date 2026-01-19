"""
视频帧处理器

职责：
- 逐帧读取视频并调用检测服务
- 协调 counter/heatmap/region_counter 的调用
- 收集每帧的检测结果和统计数据
- 支持实时处理模式和批量处理模式

处理流程：
1. 从 source 读取帧
2. 调用 detection 服务处理帧
3. 收集统计数据发送给 stats/aggregator
4. 检查告警条件发送给 alert/monitor
5. 将处理后的帧发送给 writer 或 WebSocket

被调用方：
- api/endpoints/detection.py 触发处理任务
"""
