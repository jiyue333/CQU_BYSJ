"""
DM-Count 密度图服务

通过 LWCC 库加载 DM-Count 模型，从视频帧生成密度图。
密度图同时用于热力图可视化和人数估计（density_map.sum() = count）。
"""

import tempfile
from pathlib import Path

import cv2
import numpy as np

from app.core.logger import logger


class DMCountService:
    """DM-Count 密度图服务 — 密度图生成 + 热力图渲染"""

    def __init__(
        self,
        model_name: str = "DM-Count",
        model_weights: str = "SHA",
        colormap: int = cv2.COLORMAP_JET,
        alpha: float = 0.5,
    ):
        self.model_name = model_name
        self.model_weights = model_weights
        self.colormap = colormap
        self.alpha = alpha
        self._model = None

        logger.info(f"[DMCount] 初始化: model={model_name}, weights={model_weights}")

    def _ensure_model(self):
        """懒加载模型（首次调用时加载）"""
        if self._model is None:
            from lwcc.LWCC import load_model
            self._model = load_model(self.model_name, self.model_weights)
            logger.info("[DMCount] 模型已加载")

    def predict(self, frame: np.ndarray) -> tuple[np.ndarray, float]:
        """
        从视频帧生成密度图和人数估计。

        Args:
            frame: BGR 图像帧

        Returns:
            (density_map, estimated_count)
            density_map: 二维 float32 数组，每个像素值代表该位置的人群密度
            estimated_count: 密度图求和得到的人数估计
        """
        self._ensure_model()

        # LWCC 的 get_count 需要文件路径，将帧写入临时文件
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp_path = tmp.name
            cv2.imwrite(tmp_path, frame)

        try:
            from lwcc.LWCC import get_count
            count, density_map = get_count(
                tmp_path,
                model_name=self.model_name,
                model_weights=self.model_weights,
                model=self._model,
                return_density=True,
            )
        finally:
            Path(tmp_path).unlink(missing_ok=True)

        return density_map, float(count)

    def render_heatmap(
        self,
        frame: np.ndarray,
        density_map: np.ndarray,
    ) -> np.ndarray:
        """
        将密度图渲染为热力图并叠加到原始帧上。

        Args:
            frame: BGR 输入帧
            density_map: predict() 返回的密度图

        Returns:
            叠加热力图后的 BGR 帧
        """
        h, w = frame.shape[:2]

        # 密度图可能与原始帧尺寸不同，需要缩放
        density_resized = cv2.resize(
            density_map.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR
        )

        # 归一化到 0-255
        max_val = density_resized.max()
        if max_val <= 0:
            return frame.copy()

        heatmap_normalized = (density_resized / max_val * 255).astype(np.uint8)

        # 应用 colormap
        heatmap_colored = cv2.applyColorMap(heatmap_normalized, self.colormap)

        # 创建掩码 — 只在有密度的区域叠加
        mask = heatmap_normalized > 5
        mask_3ch = np.stack([mask] * 3, axis=-1)

        # Alpha 混合
        result = frame.copy()
        blended = cv2.addWeighted(frame, 1 - self.alpha, heatmap_colored, self.alpha, 0)
        result[mask_3ch] = blended[mask_3ch]

        return result
