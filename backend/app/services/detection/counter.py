"""
实时人数统计服务

职责：
- 检测当前帧中的人数（不是进出累计计数）
- 支持全局统计（整个画面）和分区域统计
- 基于 YOLO model.track() 实现人体检测和跟踪

使用方式：
1. 全局统计：返回当前帧总人数
2. 分区域统计：返回各区域内的实时人数
   regions = {
       "entrance": [(50, 50), (250, 50), (250, 250), (50, 250)],
       "center": [(300, 100), (500, 100), (500, 300), (300, 300)],
   }

核心参数：
- regions: dict[str, list[tuple]] | None - 可选，区域定义
- classes: list[int] - 检测类别，默认 [0] 表示 person
- model: str - 模型路径，如 "yolov8n.pt"
- conf: float - 置信度阈值

输入：
- 视频帧 (numpy.ndarray)

输出：
- 标注后的帧
- total_count: int - 当前帧总人数
- region_counts: dict[str, int] - 各区域人数（如果定义了区域）
- boxes: list - 检测框坐标

实现思路：
- 使用 model.track() 获取检测结果
- 遍历检测框，判断中心点落在哪个区域
- 统计各区域人数

被调用方：
- video/processor.py 逐帧调用
- stats/aggregator.py 用于数据聚合
- alert/monitor.py 用于密度告警
"""
