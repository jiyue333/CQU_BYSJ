"""告警服务

订阅检测结果并触发告警事件，同时推送至 WebSocket 客户端。
"""

import asyncio
import json
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Optional, Set

import structlog
from fastapi import WebSocket, WebSocketDisconnect
import redis.asyncio as redis
from sqlalchemy import select

from app.core.config import settings
from app.core.database import async_session_maker
from app.core.redis import get_redis
from app.models.alert_event import AlertEvent
from app.models.alert_rule import AlertRule
from app.models.roi import ROI
from app.schemas.alert import AlertEventResponse

logger = structlog.get_logger(__name__)


@dataclass
class AlertRuleState:
    """规则运行态"""
    pending_since: Optional[float] = None
    active_event_id: Optional[str] = None
    cooldown_until: Optional[float] = None
    peak_density: float = 0.0
    count_peak: int = 0


class AlertService:
    """告警服务"""

    RESULT_STREAM_PREFIX = "result:"
    RULE_CACHE_TTL = 5
    ROI_CACHE_TTL = 30

    def __init__(self):
        self._redis: Optional[redis.Redis] = None
        self._running = False
        self._listener_task: Optional[asyncio.Task] = None

        self.connections: Set[WebSocket] = set()
        self.last_heartbeat: Dict[WebSocket, float] = {}

        # Redis stream last IDs
        self._last_ids: Dict[str, str] = {}

        # 缓存
        self._rule_cache: Dict[str, tuple[float, list[AlertRule]]] = {}
        self._roi_threshold_cache: Dict[str, tuple[float, dict]] = {}

        # 规则状态
        self._rule_states: Dict[str, AlertRuleState] = {}

    async def _get_redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = await get_redis()
        return self._redis

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._listener_task = asyncio.create_task(self._redis_listener())
        logger.info("alert_service_started")

    async def stop(self) -> None:
        self._running = False
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        logger.info("alert_service_stopped")

    async def subscribe(self, websocket: WebSocket) -> None:
        await self.start()
        await websocket.accept()
        self.connections.add(websocket)
        self.last_heartbeat[websocket] = time.time()

        try:
            while True:
                try:
                    message = await asyncio.wait_for(
                        websocket.receive_text(),
                        timeout=settings.ws_heartbeat_interval + settings.ws_heartbeat_timeout,
                    )
                    try:
                        data = json.loads(message)
                        if data.get("type") == "ping":
                            self.last_heartbeat[websocket] = time.time()
                            await websocket.send_text(json.dumps({
                                "type": "pong",
                                "ts": data.get("ts"),
                            }))
                    except json.JSONDecodeError:
                        pass
                except asyncio.TimeoutError:
                    logger.warning("alert_ws_heartbeat_timeout")
                    break
        except WebSocketDisconnect:
            logger.info("alert_ws_disconnected")
        finally:
            self._cleanup_connection(websocket)

    def _cleanup_connection(self, websocket: WebSocket) -> None:
        self.connections.discard(websocket)
        self.last_heartbeat.pop(websocket, None)

    async def _redis_listener(self) -> None:
        client = await self._get_redis()
        while self._running:
            try:
                await self._process_results(client)
                await asyncio.sleep(0.5)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("alert_service_error", error=str(e))
                await asyncio.sleep(1)

    async def _process_results(self, client: redis.Redis) -> None:
        # 获取所有 result:* streams
        cursor = 0
        stream_keys = []
        while True:
            cursor, keys = await client.scan(
                cursor=cursor,
                match=f"{self.RESULT_STREAM_PREFIX}*",
                count=100,
            )
            stream_keys.extend(keys)
            if cursor == 0:
                break

        if not stream_keys:
            return

        streams = {}
        for key in stream_keys:
            if isinstance(key, bytes):
                key = key.decode()
            stream_id = key.removeprefix(self.RESULT_STREAM_PREFIX)
            streams[key] = self._last_ids.get(stream_id, "0")

        if not streams:
            return

        messages = await client.xread(
            streams,
            count=100,
            block=0,
        )
        if not messages:
            return

        async with async_session_maker() as session:
            for stream_key, entries in messages:
                if isinstance(stream_key, bytes):
                    stream_key = stream_key.decode()
                stream_id = stream_key.removeprefix(self.RESULT_STREAM_PREFIX)

                for msg_id, data in entries:
                    if isinstance(msg_id, bytes):
                        msg_id = msg_id.decode()
                    self._last_ids[stream_id] = msg_id

                    result_data = data.get("data") or data.get(b"data", b"{}")
                    if isinstance(result_data, bytes):
                        result_data = result_data.decode()
                    try:
                        result_dict = json.loads(result_data)
                        await self._handle_result(session, result_dict)
                    except json.JSONDecodeError:
                        logger.warning("alert_invalid_result_json")
                    except Exception as e:
                        logger.error("alert_handle_result_error", error=str(e))

    async def _handle_result(self, session, result_dict: dict) -> None:
        stream_id = result_dict.get("stream_id")
        if not stream_id:
            return

        rules = await self._get_rules(session, stream_id)
        if not rules:
            return

        region_stats = result_dict.get("region_stats") or []
        total_count = int(result_dict.get("total_count") or 0)

        # 预计算全局密度最大值
        max_density = 0.0
        max_density_count = 0
        for stat in region_stats:
            density = float(stat.get("density") or 0.0)
            if density >= max_density:
                max_density = density
                max_density_count = int(stat.get("count") or 0)

        for rule in rules:
            if not rule.enabled:
                continue

            threshold_type = getattr(rule.threshold_type, "value", rule.threshold_type)
            level = getattr(rule.level, "value", rule.level)

            if rule.roi_id:
                stat = next((s for s in region_stats if s.get("region_id") == rule.roi_id), None)
                density = float(stat.get("density") or 0.0) if stat else 0.0
                count = int(stat.get("count") or 0) if stat else 0
            else:
                density = max_density
                count = total_count if threshold_type == "count" else max_density_count

            threshold_value = rule.threshold_value
            if threshold_value is None and threshold_type == "density" and rule.roi_id:
                thresholds = await self._get_roi_thresholds(session, rule.roi_id)
                threshold_value = thresholds.get(level) if thresholds else None

            if threshold_value is None:
                continue

            if threshold_type == "density":
                current_value = density
            else:
                current_value = count

            await self._apply_rule(
                session=session,
                rule=rule,
                level=level,
                density=density,
                count=count,
                threshold_value=threshold_value,
                condition_met=current_value >= threshold_value,
            )

    async def _apply_rule(
        self,
        session,
        rule: AlertRule,
        level: str,
        density: float,
        count: int,
        threshold_value: float,
        condition_met: bool,
    ) -> None:
        now = time.time()
        state = self._rule_states.setdefault(rule.id, AlertRuleState())

        if state.cooldown_until and now < state.cooldown_until:
            return

        if condition_met:
            if state.active_event_id:
                if density > state.peak_density:
                    state.peak_density = density
                if count > state.count_peak:
                    state.count_peak = count
                return

            if state.pending_since is None:
                state.pending_since = now
                return

            if now - state.pending_since < rule.min_duration_sec:
                return

            event = AlertEvent(
                id=str(uuid.uuid4()),
                rule_id=rule.id,
                stream_id=rule.stream_id,
                roi_id=rule.roi_id,
                level=level,
                start_ts=datetime.fromtimestamp(state.pending_since, tz=timezone.utc),
                end_ts=None,
                peak_density=density,
                count_peak=count,
                message=f"{rule.stream_id} 告警触发 (阈值 {threshold_value})",
                acknowledged=False,
            )
            session.add(event)
            await session.commit()

            state.active_event_id = event.id
            state.pending_since = None
            state.peak_density = density
            state.count_peak = count

            await self._broadcast_event(event)
            return

        # condition not met
        state.pending_since = None
        if state.active_event_id:
            result = await session.execute(
                select(AlertEvent).where(AlertEvent.id == state.active_event_id)
            )
            event = result.scalar_one_or_none()
            if event:
                event.end_ts = datetime.fromtimestamp(now, tz=timezone.utc)
                event.peak_density = max(event.peak_density, state.peak_density)
                event.count_peak = max(event.count_peak, state.count_peak)
                await session.commit()
                await self._broadcast_event(event)

            state.active_event_id = None
            state.cooldown_until = now + rule.cooldown_sec
            state.peak_density = 0.0
            state.count_peak = 0

    async def _get_rules(self, session, stream_id: str) -> list[AlertRule]:
        now = time.time()
        cached = self._rule_cache.get(stream_id)
        if cached and now - cached[0] < self.RULE_CACHE_TTL:
            return cached[1]

        result = await session.execute(
            select(AlertRule).where(AlertRule.stream_id == stream_id)
        )
        rules = result.scalars().all()
        self._rule_cache[stream_id] = (now, rules)
        return rules

    async def _get_roi_thresholds(self, session, roi_id: str) -> dict:
        now = time.time()
        cached = self._roi_threshold_cache.get(roi_id)
        if cached and now - cached[0] < self.ROI_CACHE_TTL:
            return cached[1]

        result = await session.execute(
            select(ROI).where(ROI.id == roi_id)
        )
        roi = result.scalar_one_or_none()
        thresholds = roi.density_thresholds if roi else {}
        self._roi_threshold_cache[roi_id] = (now, thresholds)
        return thresholds

    async def _broadcast_event(self, event: AlertEvent) -> None:
        payload = AlertEventResponse.from_orm_with_conversion(event).model_dump()
        message = json.dumps({
            "type": "alert",
            "event": payload,
        })
        for ws in self.connections.copy():
            try:
                await ws.send_text(message)
            except Exception:
                self._cleanup_connection(ws)


_alert_service: Optional[AlertService] = None


def get_alert_service() -> AlertService:
    """获取告警服务单例"""
    global _alert_service
    if _alert_service is None:
        _alert_service = AlertService()
    return _alert_service
