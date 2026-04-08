"""
实时热力图渲染器

每帧从检测点独立生成热力图，不保留历史累积。
人离开画面后热度立即消失，真正反映当前帧的人群空间分布。
"""

import cv2
import numpy as np


class RealtimeHeatmapRenderer:
    """实时热力图渲染器 — 纯快照模式"""

    def __init__(
        self,
        colormap: int = cv2.COLORMAP_JET,
        alpha: float = 0.5,
        sigma: int = 40,
        intensity: float = 1.0,
    ):
        """
        Args:
            colormap: OpenCV colormap 类型（默认 JET: 蓝→绿→黄→红）
            alpha: 热力图叠加透明度（0=完全透明, 1=完全不透明）
            sigma: 高斯核标准差（控制热力图扩散半径）
            intensity: 每个检测点的初始强度值
        """
        self.colormap = colormap
        self.alpha = alpha
        self.sigma = sigma
        self.intensity = intensity

        # 确保 sigma 为奇数（GaussianBlur 要求）
        self._ksize = self.sigma * 6 + 1  # 6σ 覆盖 99.7%
        if self._ksize % 2 == 0:
            self._ksize += 1

    def render(
        self,
        frame: np.ndarray,
        detections: list[tuple[int, int]],
    ) -> np.ndarray:
        """
        从当前帧检测点生成实时热力图并叠加到原始帧上。

        Args:
            frame: BGR 输入帧
            detections: 检测点中心坐标列表 [(cx, cy), ...]

        Returns:
            叠加热力图后的 BGR 帧
        """
        h, w = frame.shape[:2]

        if not detections:
            return frame.copy()

        # 1. 创建零矩阵
        heatmap = np.zeros((h, w), dtype=np.float32)

        # 2. 在每个检测点位置放置脉冲
        for cx, cy in detections:
            # 边界检查
            if 0 <= cx < w and 0 <= cy < h:
                heatmap[cy, cx] += self.intensity

        # 3. 高斯模糊平滑（单次卷积，高效）
        heatmap = cv2.GaussianBlur(heatmap, (self._ksize, self._ksize), self.sigma)

        # 4. 归一化到 0-255
        max_val = heatmap.max()
        if max_val > 0:
            heatmap_normalized = (heatmap / max_val * 255).astype(np.uint8)
        else:
            return frame.copy()

        # 5. 应用 colormap
        heatmap_colored = cv2.applyColorMap(heatmap_normalized, self.colormap)

        # 6. 创建掩码 — 只在有热度的区域叠加（避免蓝色背景覆盖全帧）
        mask = heatmap_normalized > 5  # 阈值过滤极低值
        mask_3ch = np.stack([mask] * 3, axis=-1)

        # 7. Alpha 混合（仅在有热度的区域）
        result = frame.copy()
        result[mask_3ch] = cv2.addWeighted(
            frame, 1 - self.alpha, heatmap_colored, self.alpha, 0
        )[mask_3ch]

        return result
