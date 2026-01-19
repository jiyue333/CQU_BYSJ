"""
视频源管理模块

职责：
- 统一管理不同类型的视频输入源
- 支持本地视频文件（mp4, avi 等）
- 支持 RTSP/RTMP 网络流
- 支持本地摄像头（设备索引 0, 1, ...）
- 提供视频元信息（宽度、高度、FPS、总帧数）

核心接口：
- open(source: str | int) -> VideoCapture
- get_info() -> dict  # width, height, fps, frame_count
- read() -> tuple[bool, numpy.ndarray]
- release() -> None

被调用方：
- processor.py 获取视频帧进行处理
- api/endpoints/video.py 处理上传的视频
"""
