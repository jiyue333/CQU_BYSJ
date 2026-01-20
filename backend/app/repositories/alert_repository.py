"""
告警记录 Repository

Alert 的数据库操作
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.alert import Alert


class AlertRepository:
    """告警仓储"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, alert: Alert) -> Alert:
        """创建告警记录"""
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        return alert

    def get_by_id(self, alert_id: str) -> Optional[Alert]:
        """根据 ID 获取告警"""
        return self.db.get(Alert, alert_id)

    def get_by_source_id(
        self,
        source_id: str,
        skip: int = 0,
        limit: int = 100,
        level: Optional[str] = None,
    ) -> list[Alert]:
        """获取数据源的告警列表"""
        stmt = select(Alert).where(Alert.source_id == source_id)
        if level:
            stmt = stmt.where(Alert.level == level)
        stmt = stmt.order_by(Alert.timestamp.desc()).offset(skip).limit(limit)
        return list(self.db.scalars(stmt).all())

    def get_unacknowledged(self, source_id: str) -> list[Alert]:
        """获取未确认的告警"""
        stmt = (
            select(Alert)
            .where(Alert.source_id == source_id, Alert.is_acknowledged == 0)
            .order_by(Alert.timestamp.desc())
        )
        return list(self.db.scalars(stmt).all())

    def get_by_time_range(
        self,
        source_id: str,
        time_from: str,
        time_to: str,
        level: Optional[str] = None,
    ) -> list[Alert]:
        """按时间范围查询告警"""
        stmt = select(Alert).where(
            Alert.source_id == source_id,
            Alert.timestamp >= time_from,
            Alert.timestamp <= time_to,
        )
        if level:
            stmt = stmt.where(Alert.level == level)
        stmt = stmt.order_by(Alert.timestamp.desc())
        return list(self.db.scalars(stmt).all())

    def acknowledge(self, alert_id: str) -> Optional[Alert]:
        """确认告警"""
        alert = self.get_by_id(alert_id)
        if alert:
            alert.is_acknowledged = 1
            alert.acknowledged_at = datetime.utcnow().isoformat() + "Z"
            self.db.commit()
            self.db.refresh(alert)
            return alert
        return None

    def acknowledge_all(self, source_id: str) -> int:
        """确认数据源的所有告警"""
        alerts = self.get_unacknowledged(source_id)
        now = datetime.utcnow().isoformat() + "Z"
        for alert in alerts:
            alert.is_acknowledged = 1
            alert.acknowledged_at = now
        self.db.commit()
        return len(alerts)

    def count_by_source(self, source_id: str, level: Optional[str] = None) -> int:
        """统计告警数量"""
        stmt = select(func.count()).select_from(Alert).where(Alert.source_id == source_id)
        if level:
            stmt = stmt.where(Alert.level == level)
        return self.db.scalar(stmt) or 0

    def count_unacknowledged(self, source_id: str) -> int:
        """统计未确认告警数量"""
        stmt = (
            select(func.count())
            .select_from(Alert)
            .where(Alert.source_id == source_id, Alert.is_acknowledged == 0)
        )
        return self.db.scalar(stmt) or 0

    def delete(self, alert_id: str) -> bool:
        """删除告警"""
        alert = self.get_by_id(alert_id)
        if alert:
            self.db.delete(alert)
            self.db.commit()
            return True
        return False

    def delete_old_alerts(self, source_id: str, before: str) -> int:
        """删除旧告警"""
        stmt = select(Alert).where(Alert.source_id == source_id, Alert.timestamp < before)
        alerts = list(self.db.scalars(stmt).all())
        count = len(alerts)
        for alert in alerts:
            self.db.delete(alert)
        self.db.commit()
        return count
