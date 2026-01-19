"""
热力图生成服务

职责：
- 封装 ultralytics.solutions.Heatmap
- 基于人流轨迹生成密度热力图
- 支持自定义 colormap（PARULA, JET, INFERNO 等）
- 可选：结合区域进行区域内热力图统计

核心参数：
- colormap: int - OpenCV colormap，如 cv2.COLORMAP_PARULA
- region: list[tuple] - 可选，限定热力图生成区域
- classes: list[int] - 检测类别，默认 [0]

输入：
- 视频帧 (numpy.ndarray)

输出：
- 热力图叠加后的帧 (results.plot_im)
- 检测框信息 (boxes, confs, clss)

被调用方：
- video/processor.py 逐帧调用
- 前端热力图可视化面板
"""
