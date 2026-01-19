"""
基础检测器模块

职责：
- 加载和管理 YOLO 模型实例
- 提供模型配置（置信度阈值、设备选择等）
- 作为其他检测服务的基类或依赖

依赖：
- ultralytics.YOLO

被调用方：
- counter.py, heatmap.py, region_counter.py 继承或组合使用
"""
