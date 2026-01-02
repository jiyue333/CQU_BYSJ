"""告警相关 REST API"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.alert_event import AlertEvent
from app.models.alert_rule import AlertRule
from app.models.roi import ROI
from app.models.video_stream import VideoStream
from app.schemas.alert import (
    AlertEventListResponse,
    AlertEventResponse,
    AlertRuleCreate,
    AlertRuleListResponse,
    AlertRuleResponse,
    AlertRuleUpdate,
)

router = APIRouter()


async def _get_stream_or_404(db: AsyncSession, stream_id: str) -> VideoStream:
    result = await db.execute(
        select(VideoStream).where(VideoStream.id == stream_id)
    )
    stream = result.scalar_one_or_none()
    if not stream:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stream {stream_id} not found"
        )
    return stream


async def _get_roi_or_404(db: AsyncSession, roi_id: str, stream_id: Optional[str] = None) -> ROI:
    stmt = select(ROI).where(ROI.id == roi_id)
    if stream_id:
        stmt = stmt.where(ROI.stream_id == stream_id)
    result = await db.execute(stmt)
    roi = result.scalar_one_or_none()
    if not roi:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ROI {roi_id} not found"
        )
    return roi


async def _get_rule_or_404(db: AsyncSession, rule_id: str) -> AlertRule:
    result = await db.execute(
        select(AlertRule).where(AlertRule.id == rule_id)
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert rule {rule_id} not found"
        )
    return rule


@router.get(
    "/rules",
    response_model=AlertRuleListResponse,
    summary="获取告警规则列表",
)
async def list_alert_rules(
    stream_id: Optional[str] = Query(None, description="视频流 ID"),
    db: AsyncSession = Depends(get_db),
) -> AlertRuleListResponse:
    stmt = select(AlertRule)
    if stream_id:
        stmt = stmt.where(AlertRule.stream_id == stream_id)
    result = await db.execute(stmt.order_by(AlertRule.created_at))
    rules = result.scalars().all()
    return AlertRuleListResponse(
        rules=[AlertRuleResponse.model_validate(rule) for rule in rules],
        total=len(rules),
    )


@router.post(
    "/rules",
    response_model=AlertRuleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建告警规则",
)
async def create_alert_rule(
    data: AlertRuleCreate,
    db: AsyncSession = Depends(get_db),
) -> AlertRuleResponse:
    await _get_stream_or_404(db, data.stream_id)
    if data.roi_id:
        await _get_roi_or_404(db, data.roi_id, data.stream_id)

    rule = AlertRule(
        id=str(uuid.uuid4()),
        stream_id=data.stream_id,
        roi_id=data.roi_id,
        threshold_type=data.threshold_type,
        threshold_value=data.threshold_value,
        level=data.level,
        min_duration_sec=data.min_duration_sec,
        cooldown_sec=data.cooldown_sec,
        enabled=data.enabled,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return AlertRuleResponse.model_validate(rule)


@router.put(
    "/rules/{rule_id}",
    response_model=AlertRuleResponse,
    summary="更新告警规则",
)
async def update_alert_rule(
    rule_id: str,
    data: AlertRuleUpdate,
    db: AsyncSession = Depends(get_db),
) -> AlertRuleResponse:
    rule = await _get_rule_or_404(db, rule_id)

    update_data = data.model_dump(exclude_unset=True)
    if "roi_id" in update_data and update_data["roi_id"]:
        await _get_roi_or_404(db, update_data["roi_id"], rule.stream_id)

    for field, value in update_data.items():
        setattr(rule, field, value)

    await db.commit()
    await db.refresh(rule)
    return AlertRuleResponse.model_validate(rule)


@router.delete(
    "/rules/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除告警规则",
)
async def delete_alert_rule(
    rule_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    rule = await _get_rule_or_404(db, rule_id)
    await db.delete(rule)
    await db.commit()


@router.get(
    "/events",
    response_model=AlertEventListResponse,
    summary="获取告警事件历史",
)
async def list_alert_events(
    stream_id: Optional[str] = Query(None, description="视频流 ID"),
    start_ts: Optional[float] = Query(None, description="起始时间戳"),
    end_ts: Optional[float] = Query(None, description="结束时间戳"),
    limit: int = Query(50, ge=1, le=200, description="分页大小"),
    offset: int = Query(0, ge=0, description="偏移量"),
    db: AsyncSession = Depends(get_db),
) -> AlertEventListResponse:
    stmt = select(AlertEvent)
    if stream_id:
        stmt = stmt.where(AlertEvent.stream_id == stream_id)
    if start_ts is not None:
        stmt = stmt.where(
            AlertEvent.start_ts >= datetime.fromtimestamp(start_ts, tz=timezone.utc)
        )
    if end_ts is not None:
        stmt = stmt.where(
            AlertEvent.start_ts <= datetime.fromtimestamp(end_ts, tz=timezone.utc)
        )

    result = await db.execute(
        stmt.order_by(AlertEvent.start_ts.desc()).offset(offset).limit(limit)
    )
    events = result.scalars().all()
    return AlertEventListResponse(
        events=[AlertEventResponse.from_orm_with_conversion(event) for event in events],
        total=len(events),
    )


@router.post(
    "/events/{event_id}/acknowledge",
    response_model=AlertEventResponse,
    summary="确认告警",
)
async def acknowledge_alert(
    event_id: str,
    db: AsyncSession = Depends(get_db),
) -> AlertEventResponse:
    result = await db.execute(
        select(AlertEvent).where(AlertEvent.id == event_id)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert event {event_id} not found"
        )
    event.acknowledged = True
    await db.commit()
    await db.refresh(event)
    return AlertEventResponse.from_orm_with_conversion(event)
