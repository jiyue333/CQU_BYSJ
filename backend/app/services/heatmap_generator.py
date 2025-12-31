"""热力图生成器

根据检测位置生成热力图网格，使用 EMA 平滑算法。

EMA 公式: EMA_t = α * value_t + (1-α) * EMA_{t-1}
- α (alpha) = 0.3（默认）
- 初始值处理：第一帧直接使用原始值
"""

from typing import Optional

import numpy as np

from app.core.config import settings
from app.schemas.detection import Detection


class HeatmapGenerator:
    """热力图生成器
    
    职责：
    1. 根据检测位置生成热力图网格
    2. 使用 EMA 平滑算法实现平滑过渡
    3. 按 stream_id 维护独立的 EMA 状态
    """
    
    def __init__(
        self,
        grid_size: int = settings.heatmap_grid_size,
        alpha: float = settings.heatmap_decay,
    ):
        """初始化热力图生成器
        
        Args:
            grid_size: 网格大小（默认 20x20）
            alpha: EMA 平滑因子（默认 0.3）
        """
        self.grid_size = grid_size
        self.alpha = alpha
        
        # 每个 stream_id 的 EMA 状态
        self._ema_grids: dict[str, np.ndarray] = {}
    
    def generate(
        self,
        stream_id: str,
        detections: list[Detection],
        frame_width: int,
        frame_height: int,
    ) -> list[list[float]]:
        """生成热力图网格
        
        Args:
            stream_id: 视频流 ID
            detections: 检测结果列表
            frame_width: 帧宽度（像素）
            frame_height: 帧高度（像素）
            
        Returns:
            热力图网格（grid_size x grid_size），值范围 0-1
        """
        # 1. 计算原始热力图
        raw_grid = self._compute_raw_grid(detections, frame_width, frame_height)
        
        # 2. 归一化
        normalized_grid = self._normalize_grid(raw_grid)
        
        # 3. EMA 平滑
        ema_grid = self._apply_ema(stream_id, normalized_grid)
        
        # 4. 转换为列表格式
        return ema_grid.tolist()
    
    def _compute_raw_grid(
        self,
        detections: list[Detection],
        frame_width: int,
        frame_height: int,
    ) -> np.ndarray:
        """计算原始热力图网格
        
        使用检测框中心点映射到网格，累加计数。
        
        Args:
            detections: 检测结果列表
            frame_width: 帧宽度
            frame_height: 帧高度
            
        Returns:
            原始计数网格
        """
        grid = np.zeros((self.grid_size, self.grid_size), dtype=np.float32)
        
        if frame_width <= 0 or frame_height <= 0:
            return grid
        
        # 计算每个网格单元的大小
        cell_width = frame_width / self.grid_size
        cell_height = frame_height / self.grid_size
        
        for detection in detections:
            # 获取检测框中心点
            center_x, center_y = detection.center
            
            # 映射到网格坐标
            grid_x = int(center_x / cell_width)
            grid_y = int(center_y / cell_height)
            
            # 边界检查
            grid_x = max(0, min(grid_x, self.grid_size - 1))
            grid_y = max(0, min(grid_y, self.grid_size - 1))
            
            # 累加计数
            grid[grid_y, grid_x] += 1.0
        
        return grid
    
    def _normalize_grid(self, grid: np.ndarray) -> np.ndarray:
        """归一化网格到 0-1 范围
        
        Args:
            grid: 原始计数网格
            
        Returns:
            归一化后的网格
        """
        max_val = grid.max()
        if max_val > 0:
            return grid / max_val
        return grid
    
    def _apply_ema(self, stream_id: str, current_grid: np.ndarray) -> np.ndarray:
        """应用 EMA 平滑
        
        EMA_t = α * value_t + (1-α) * EMA_{t-1}
        
        Args:
            stream_id: 视频流 ID
            current_grid: 当前帧的归一化网格
            
        Returns:
            EMA 平滑后的网格
        """
        if stream_id not in self._ema_grids:
            # 首帧：直接使用原始值
            self._ema_grids[stream_id] = current_grid.copy()
        else:
            # 后续帧：应用 EMA
            prev_ema = self._ema_grids[stream_id]
            self._ema_grids[stream_id] = (
                self.alpha * current_grid + (1 - self.alpha) * prev_ema
            )
        
        return self._ema_grids[stream_id].copy()
    
    def reset(self, stream_id: str) -> None:
        """重置某路流的 EMA 状态
        
        Args:
            stream_id: 视频流 ID
        """
        if stream_id in self._ema_grids:
            del self._ema_grids[stream_id]
    
    def reset_all(self) -> None:
        """重置所有 EMA 状态"""
        self._ema_grids.clear()
    
    def get_ema_state(self, stream_id: str) -> Optional[np.ndarray]:
        """获取某路流的 EMA 状态（用于测试）
        
        Args:
            stream_id: 视频流 ID
            
        Returns:
            EMA 网格，如果不存在则返回 None
        """
        return self._ema_grids.get(stream_id)
    
    def has_state(self, stream_id: str) -> bool:
        """检查是否有某路流的 EMA 状态
        
        Args:
            stream_id: 视频流 ID
            
        Returns:
            True 如果存在状态
        """
        return stream_id in self._ema_grids


# 便捷函数
def generate_heatmap(
    detections: list[Detection],
    frame_width: int,
    frame_height: int,
    grid_size: int = 20,
) -> list[list[float]]:
    """生成热力图（无 EMA 平滑）
    
    这是一个无状态的便捷函数，用于单次生成热力图。
    
    Args:
        detections: 检测结果列表
        frame_width: 帧宽度
        frame_height: 帧高度
        grid_size: 网格大小
        
    Returns:
        热力图网格
    """
    generator = HeatmapGenerator(grid_size=grid_size, alpha=1.0)
    return generator.generate("temp", detections, frame_width, frame_height)


def compute_raw_heatmap(
    detections: list[Detection],
    frame_width: int,
    frame_height: int,
    grid_size: int = 20,
) -> list[list[float]]:
    """计算原始热力图（未归一化）
    
    用于属性测试。
    
    Args:
        detections: 检测结果列表
        frame_width: 帧宽度
        frame_height: 帧高度
        grid_size: 网格大小
        
    Returns:
        原始计数网格
    """
    generator = HeatmapGenerator(grid_size=grid_size)
    raw_grid = generator._compute_raw_grid(detections, frame_width, frame_height)
    return raw_grid.tolist()
