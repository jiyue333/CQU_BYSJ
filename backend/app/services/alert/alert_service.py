"""
告警服务

提供：
- 区域人数/密度阈值判断
- 告警级别（warning/critical）
- 告警记录生成
- 防抖/冷却机制
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional


class AlertLevel(Enum):
    """告警级别"""

    WARNING = "warning"  # 接近阈值
    CRITICAL = "critical"  # 超过阈值


class AlertType(Enum):
    """告警类型"""

    REGION_COUNT = "region_count"  # 区域人数告警
    REGION_DENSITY = "region_density"  # 区域密度告警


@dataclass
class Alert:
    """告警记录"""

    alert_id: str
    alert_type: AlertType
    level: AlertLevel
    current_value: float
    threshold: float
    timestamp: datetime
    region_id: str
    region_name: str

    def to_dict(self) -> dict:
        """转换为字典（用于 JSON 序列化）"""
        return {
            "alert_id": self.alert_id,
            "alert_type": self.alert_type.value,
            "level": self.level.value,
            "current_value": self.current_value,
            "threshold": self.threshold,
            "timestamp": self.timestamp.isoformat(),
            "region_id": self.region_id,
            "region_name": self.region_name,
        }


@dataclass
class RegionThresholdConfig:
    """区域阈值配置"""

    region_id: str
    region_name: str
    count_warning: Optional[int] = None
    count_critical: Optional[int] = None
    density_warning: Optional[float] = None
    density_critical: Optional[float] = None


@dataclass
class RegionAlertMetrics:
    """区域告警评估输入"""

    region_id: str
    region_name: str
    count: float
    density: float


class AlertService:
    """告警服务 - 基于区域配置的阈值检查"""

    def __init__(self, cooldown_seconds: int = 30):
        """
        Args:
            cooldown_seconds: 冷却时间（秒），同一区域告警在此时间内不重复触发
        """
        self.cooldown_seconds = cooldown_seconds
        # 区域阈值配置 {region_id: RegionThresholdConfig}
        self._region_configs: dict[str, RegionThresholdConfig] = {}
        # key: "count:{region_id}" 或 "density:{region_id}"
        self._last_alert_time: dict[str, datetime] = {}

    def set_region_thresholds(self, configs: list[RegionThresholdConfig]) -> None:
        """设置区域阈值配置"""
        self._region_configs = {c.region_id: c for c in configs}

    def check(
        self,
        region_metrics: dict[str, RegionAlertMetrics],
    ) -> list[Alert]:
        """
        检查区域指标是否触发告警

        Args:
            region_metrics: 按区域 ID 聚合的实时人数和密度

        Returns:
            触发的告警列表（可能为空）
        """
        alerts: list[Alert] = []
        now = datetime.now()

        # 检查各区域人数
        for region_id, metrics in region_metrics.items():
            config = self._region_configs.get(region_id)
            if not config:
                continue

            count_alert = self._check_count(metrics, config, now)
            if count_alert:
                alerts.append(count_alert)

            density_alert = self._check_density(metrics, config, now)
            if density_alert:
                alerts.append(density_alert)

        return alerts

    def _check_count(
        self, metrics: RegionAlertMetrics, config: RegionThresholdConfig, now: datetime
    ) -> Optional[Alert]:
        """检查区域人数告警"""
        warning_th = config.count_warning
        critical_th = config.count_critical

        # 如果没有配置阈值，不检查
        if warning_th is None and critical_th is None:
            return None

        level = self._get_level(metrics.count, warning_th, critical_th)
        if not level:
            return None

        # 冷却检查
        cooldown_key = f"count:{metrics.region_id}"
        if not self._check_cooldown(cooldown_key, now):
            return None

        threshold = critical_th if level == AlertLevel.CRITICAL else warning_th
        return Alert(
            alert_id=str(uuid.uuid4()),
            alert_type=AlertType.REGION_COUNT,
            level=level,
            current_value=metrics.count,
            threshold=threshold,
            timestamp=now,
            region_id=metrics.region_id,
            region_name=metrics.region_name,
        )

    def _check_density(
        self, metrics: RegionAlertMetrics, config: RegionThresholdConfig, now: datetime
    ) -> Optional[Alert]:
        """检查区域密度告警"""
        warning_th = config.density_warning
        critical_th = config.density_critical

        # 如果没有配置阈值，不检查
        if warning_th is None and critical_th is None:
            return None

        level = self._get_level(metrics.density, warning_th, critical_th)
        if not level:
            return None

        # 冷却检查
        cooldown_key = f"density:{metrics.region_id}"
        if not self._check_cooldown(cooldown_key, now):
            return None

        threshold = critical_th if level == AlertLevel.CRITICAL else warning_th
        return Alert(
            alert_id=str(uuid.uuid4()),
            alert_type=AlertType.REGION_DENSITY,
            level=level,
            current_value=metrics.density,
            threshold=threshold,
            timestamp=now,
            region_id=metrics.region_id,
            region_name=metrics.region_name,
        )

    def _get_level(
        self, value: float, warning_threshold: Optional[float], critical_threshold: Optional[float]
    ) -> Optional[AlertLevel]:
        """根据当前值和阈值判断告警级别"""
        if critical_threshold is not None and value >= critical_threshold:
            return AlertLevel.CRITICAL
        elif warning_threshold is not None and value >= warning_threshold:
            return AlertLevel.WARNING
        return None

    def _check_cooldown(self, key: str, now: datetime) -> bool:
        """
        检查是否在冷却时间外

        Returns:
            True: 可以触发告警
            False: 在冷却时间内，不触发
        """
        last_time = self._last_alert_time.get(key)
        cooldown = timedelta(seconds=self.cooldown_seconds)

        if last_time and (now - last_time) < cooldown:
            return False

        # 更新最后告警时间
        self._last_alert_time[key] = now
        return True

    def reset_cooldown(self) -> None:
        """重置所有冷却时间"""
        self._last_alert_time.clear()
