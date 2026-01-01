"""DetectionResult Pydantic Schemas

检测结果相关的数据模型。这些模型用于实时数据传输（通过 Redis Streams），
不需要持久化到数据库。
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class DensityLevel(str, Enum):
    """密度等级枚举
    
    根据密度阈值分类：
    - LOW: density < low_threshold
    - MEDIUM: low_threshold <= density < medium_threshold
    - HIGH: density >= medium_threshold
    """
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Detection(BaseModel):
    """单个检测结果
    
    表示 YOLO 检测到的一个人体边界框。
    """
    x: int = Field(..., ge=0, description="边界框左上角 X 坐标")
    y: int = Field(..., ge=0, description="边界框左上角 Y 坐标")
    width: int = Field(..., gt=0, description="边界框宽度")
    height: int = Field(..., gt=0, description="边界框高度")
    confidence: float = Field(..., ge=0.0, le=1.0, description="检测置信度")

    @property
    def center(self) -> tuple[float, float]:
        """获取边界框中心点坐标"""
        return (self.x + self.width / 2, self.y + self.height / 2)

    @property
    def area(self) -> int:
        """获取边界框面积"""
        return self.width * self.height


class RegionStat(BaseModel):
    """区域统计结果
    
    表示某个 ROI 区域的人数和密度统计。
    """
    region_id: str = Field(..., description="区域 ID")
    region_name: str = Field(..., description="区域名称")
    count: int = Field(..., ge=0, description="区域内人数")
    density: float = Field(..., ge=0.0, le=1.0, description="密度值（0-1）")
    level: DensityLevel = Field(..., description="密度等级")


class DetectionResult(BaseModel):
    """完整检测结果
    
    包含一帧图像的所有检测信息，通过 Redis Streams 推送给前端。
    """
    stream_id: str = Field(..., description="视频流 ID")
    capture_ts: Optional[float] = Field(
        None, description="快照采集时间戳（epoch）"
    )
    timestamp: float = Field(..., description="检测完成时间戳（epoch）")
    total_count: int = Field(..., ge=0, description="总人数")
    frame_width: int = Field(default=1920, ge=1, description="帧宽度（像素）")
    frame_height: int = Field(default=1080, ge=1, description="帧高度（像素）")
    detections: list[Detection] = Field(default_factory=list, description="检测框列表")
    heatmap_grid: list[list[float]] = Field(
        default_factory=list, 
        description="热力图网格（如 20x20）"
    )
    region_stats: list[RegionStat] = Field(
        default_factory=list, 
        description="各区域统计"
    )

    @field_validator("heatmap_grid")
    @classmethod
    def validate_heatmap_grid(cls, v: list[list[float]]) -> list[list[float]]:
        """验证热力图网格格式"""
        if not v:
            return v
        
        # 检查是否为矩形网格
        row_lengths = [len(row) for row in v]
        if len(set(row_lengths)) > 1:
            raise ValueError("热力图网格必须是矩形（所有行长度相同）")
        
        # 检查值范围
        for row in v:
            for val in row:
                if not (0.0 <= val <= 1.0):
                    raise ValueError("热力图值必须在 0-1 范围内")
        
        return v

    @property
    def detection_count(self) -> int:
        """获取检测框数量"""
        return len(self.detections)

    def get_region_stat(self, region_id: str) -> Optional[RegionStat]:
        """根据区域 ID 获取统计结果"""
        for stat in self.region_stats:
            if stat.region_id == region_id:
                return stat
        return None
