"""ROI 区域计算器

实现多边形面积计算（Shoelace 公式）和点在多边形内判断（射线法）。
用于计算各 ROI 区域的人数密度。
"""

from typing import Optional

from app.schemas.detection import Detection, DensityLevel, RegionStat
from app.schemas.roi import DensityThresholds, Point


class ROICalculator:
    """ROI 区域计算器
    
    职责：
    1. 计算多边形面积（Shoelace 公式）
    2. 判断点是否在多边形内（射线法）
    3. 计算区域密度和等级
    """
    
    # 面积归一化因子（用于将像素面积转换为密度）
    AREA_NORMALIZATION_FACTOR = 5000.0
    
    @staticmethod
    def polygon_area(points: list[Point]) -> float:
        """计算多边形面积（Shoelace 公式）
        
        公式: Area = 0.5 × |Σ(x_i × y_{i+1} - x_{i+1} × y_i)|
        
        Args:
            points: 多边形顶点列表（至少 3 个点）
            
        Returns:
            多边形面积（像素平方）
            
        Raises:
            ValueError: 顶点数少于 3
        """
        if len(points) < 3:
            raise ValueError("多边形至少需要 3 个顶点")
        
        n = len(points)
        area = 0.0
        
        for i in range(n):
            j = (i + 1) % n
            area += points[i].x * points[j].y
            area -= points[j].x * points[i].y
        
        return abs(area) / 2.0
    
    @staticmethod
    def point_in_polygon(
        point: tuple[float, float],
        polygon: list[Point],
        on_boundary_is_inside: bool = True,
    ) -> bool:
        """判断点是否在多边形内（射线法）
        
        从点向右发射水平射线，计算与多边形边的交点数。
        奇数则在内部，偶数则在外部。
        
        Args:
            point: 待判断的点 (x, y)
            polygon: 多边形顶点列表
            on_boundary_is_inside: 点在边界上是否算作在内部
            
        Returns:
            True 如果点在多边形内部（或边界上，取决于参数）
        """
        if len(polygon) < 3:
            return False
        
        x, y = point
        n = len(polygon)
        inside = False
        
        j = n - 1
        for i in range(n):
            xi, yi = polygon[i].x, polygon[i].y
            xj, yj = polygon[j].x, polygon[j].y
            
            # 检查点是否在边界上
            if on_boundary_is_inside:
                if ROICalculator._point_on_segment(x, y, xi, yi, xj, yj):
                    return True
            
            # 射线法核心逻辑
            if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                inside = not inside
            
            j = i
        
        return inside
    
    @staticmethod
    def _point_on_segment(
        px: float, py: float,
        x1: float, y1: float,
        x2: float, y2: float,
        epsilon: float = 1e-9,
    ) -> bool:
        """判断点是否在线段上
        
        Args:
            px, py: 点坐标
            x1, y1, x2, y2: 线段端点坐标
            epsilon: 浮点容差
            
        Returns:
            True 如果点在线段上
        """
        # 检查点是否在线段的边界框内
        if not (min(x1, x2) - epsilon <= px <= max(x1, x2) + epsilon and
                min(y1, y2) - epsilon <= py <= max(y1, y2) + epsilon):
            return False
        
        # 计算叉积判断共线
        cross = (py - y1) * (x2 - x1) - (px - x1) * (y2 - y1)
        return abs(cross) < epsilon
    
    @classmethod
    def count_detections_in_region(
        cls,
        detections: list[Detection],
        polygon: list[Point],
    ) -> int:
        """统计区域内的检测数量
        
        使用检测框中心点判断是否在区域内。
        
        Args:
            detections: 检测结果列表
            polygon: 区域多边形顶点
            
        Returns:
            区域内的检测数量
        """
        count = 0
        for detection in detections:
            center = detection.center
            if cls.point_in_polygon(center, polygon):
                count += 1
        return count
    
    @classmethod
    def calculate_density(
        cls,
        count: int,
        area: float,
        normalization_factor: Optional[float] = None,
    ) -> float:
        """计算密度值
        
        密度 = count / (area / normalization_factor)
        归一化到 0-1 范围。
        
        Args:
            count: 区域内人数
            area: 区域面积（像素平方）
            normalization_factor: 面积归一化因子
            
        Returns:
            密度值（0-1）
        """
        if area <= 0:
            return 0.0
        
        factor = normalization_factor or cls.AREA_NORMALIZATION_FACTOR
        raw_density = count / (area / factor)
        
        # 归一化到 0-1
        return min(1.0, max(0.0, raw_density))
    
    @staticmethod
    def classify_density_level(
        density: float,
        thresholds: DensityThresholds,
    ) -> DensityLevel:
        """根据阈值分类密度等级
        
        分类规则：
        - LOW: density < low_threshold
        - MEDIUM: low_threshold <= density < medium_threshold
        - HIGH: density >= medium_threshold
        
        Args:
            density: 密度值（0-1）
            thresholds: 密度阈值配置
            
        Returns:
            密度等级
        """
        if density >= thresholds.medium:
            return DensityLevel.HIGH
        elif density >= thresholds.low:
            return DensityLevel.MEDIUM
        else:
            return DensityLevel.LOW
    
    @classmethod
    def calculate_region_stat(
        cls,
        region_id: str,
        region_name: str,
        polygon: list[Point],
        thresholds: DensityThresholds,
        detections: list[Detection],
    ) -> RegionStat:
        """计算单个区域的统计结果
        
        Args:
            region_id: 区域 ID
            region_name: 区域名称
            polygon: 区域多边形顶点
            thresholds: 密度阈值配置
            detections: 检测结果列表
            
        Returns:
            区域统计结果
        """
        # 计算面积
        area = cls.polygon_area(polygon)
        
        # 统计区域内人数
        count = cls.count_detections_in_region(detections, polygon)
        
        # 计算密度
        density = cls.calculate_density(count, area)
        
        # 分类等级
        level = cls.classify_density_level(density, thresholds)
        
        return RegionStat(
            region_id=region_id,
            region_name=region_name,
            count=count,
            density=round(density, 4),
            level=level,
        )


# 便捷函数
def polygon_area(points: list[Point]) -> float:
    """计算多边形面积"""
    return ROICalculator.polygon_area(points)


def point_in_polygon(point: tuple[float, float], polygon: list[Point]) -> bool:
    """判断点是否在多边形内"""
    return ROICalculator.point_in_polygon(point, polygon)


def calculate_density(count: int, area: float) -> float:
    """计算密度值"""
    return ROICalculator.calculate_density(count, area)


def classify_density_level(density: float, thresholds: DensityThresholds) -> DensityLevel:
    """分类密度等级"""
    return ROICalculator.classify_density_level(density, thresholds)
