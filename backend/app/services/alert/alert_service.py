"""
告警服务

提供：
- 阈值判断（总人数/区域人数）
- 告警级别（warning/critical）
- 告警记录生成
- 防抖/冷却机制
- 告警配置管理
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from app.services.detection import DetectionResult


class AlertLevel(Enum):
    """告警级别"""

    WARNING = "warning"  # 接近阈值
    CRITICAL = "critical"  # 超过阈值


class AlertType(Enum):
    """告警类型"""

    TOTAL_COUNT = "total_count"  # 总人数告警
    REGION_COUNT = "region_count"  # 区域人数告警


@dataclass
class Alert:
    """告警记录"""

    alert_id: str
    alert_type: AlertType
    level: AlertLevel
    current_value: int
    threshold: int
    timestamp: datetime
    region_name: str | None = None  # 区域告警时有值

    def to_dict(self) -> dict:
        """转换为字典（用于 JSON 序列化）"""
        return {
            "alert_id": self.alert_id,
            "alert_type": self.alert_type.value,
            "level": self.level.value,
            "current_value": self.current_value,
            "threshold": self.threshold,
            "timestamp": self.timestamp.isoformat(),
            "region_name": self.region_name,
        }


@dataclass
class AlertConfig:
    """告警配置"""

    # 总人数阈值
    total_warning_threshold: int = 50  # 警告阈值
    total_critical_threshold: int = 100  # 严重阈值

    # 区域人数阈值（可按区域单独配置）
    region_thresholds: dict[str, tuple[int, int]] = field(default_factory=dict)
    # {"区域名": (warning_threshold, critical_threshold)}

    # 默认区域阈值（未单独配置的区域使用）
    default_region_warning: int = 20
    default_region_critical: int = 50

    # 冷却时间（秒），同一类型告警在此时间内不重复触发
    cooldown_seconds: int = 30

    # 是否启用告警
    enabled: bool = True


class AlertService:
    """告警服务"""

    def __init__(self, config: AlertConfig | None = None):
        """
        Args:
            config: 告警配置，不传则使用默认配置
        """
        self.config = config or AlertConfig()
        # 记录上次告警时间，用于冷却判断
        # key: "total" 或 "region:{region_name}"
        self._last_alert_time: dict[str, datetime] = {}

    def check(self, result: DetectionResult) -> list[Alert]:
        """
        检查检测结果是否触发告警

        Args:
            result: 检测结果

        Returns:
            触发的告警列表（可能为空）
        """
        if not self.config.enabled:
            return []

        alerts: list[Alert] = []
        now = datetime.now()

        # 检查总人数
        total_alert = self._check_total(result.total_count, now)
        if total_alert:
            alerts.append(total_alert)

        # 检查各区域人数
        for region_name, count in result.region_counts.items():
            region_alert = self._check_region(region_name, count, now)
            if region_alert:
                alerts.append(region_alert)

        # TODO: 保存告警到数据库
        # for alert in alerts:
        #     db.save_alert(alert)

        return alerts

    def _check_total(self, count: int, now: datetime) -> Alert | None:
        """检查总人数告警"""
        warning_th = self.config.total_warning_threshold
        critical_th = self.config.total_critical_threshold

        level = self._get_level(count, warning_th, critical_th)
        if not level:
            return None

        # 冷却检查
        if not self._check_cooldown("total", now):
            return None

        threshold = critical_th if level == AlertLevel.CRITICAL else warning_th
        return Alert(
            alert_id=str(uuid.uuid4()),
            alert_type=AlertType.TOTAL_COUNT,
            level=level,
            current_value=count,
            threshold=threshold,
            timestamp=now,
        )

    def _check_region(
        self, region_name: str, count: int, now: datetime
    ) -> Alert | None:
        """检查区域人数告警"""
        # 获取该区域的阈值配置
        if region_name in self.config.region_thresholds:
            warning_th, critical_th = self.config.region_thresholds[region_name]
        else:
            warning_th = self.config.default_region_warning
            critical_th = self.config.default_region_critical

        level = self._get_level(count, warning_th, critical_th)
        if not level:
            return None

        # 冷却检查
        cooldown_key = f"region:{region_name}"
        if not self._check_cooldown(cooldown_key, now):
            return None

        threshold = critical_th if level == AlertLevel.CRITICAL else warning_th
        return Alert(
            alert_id=str(uuid.uuid4()),
            alert_type=AlertType.REGION_COUNT,
            level=level,
            current_value=count,
            threshold=threshold,
            timestamp=now,
            region_name=region_name,
        )

    def _get_level(
        self, count: int, warning_threshold: int, critical_threshold: int
    ) -> AlertLevel | None:
        """根据当前值和阈值判断告警级别"""
        if count >= critical_threshold:
            return AlertLevel.CRITICAL
        elif count >= warning_threshold:
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
        cooldown = timedelta(seconds=self.config.cooldown_seconds)

        if last_time and (now - last_time) < cooldown:
            return False

        # 更新最后告警时间
        self._last_alert_time[key] = now
        return True

    def update_config(self, **kwargs) -> None:
        """更新配置"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)

    def reset_cooldown(self) -> None:
        """重置所有冷却时间"""
        self._last_alert_time.clear()
