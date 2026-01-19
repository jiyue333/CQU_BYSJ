"""
视频结果写入模块

职责：
- 将检测标注后的视频帧写入输出文件
- 支持多种输出格式（mp4, avi）
- 管理输出文件路径（uploads/results/）

核心接口：
- create(output_path: str, width: int, height: int, fps: float)
- write(frame: numpy.ndarray)
- release() -> str  # 返回输出文件路径

被调用方：
- processor.py 写入处理后的帧
"""
