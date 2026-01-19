"""
告警通知模块

职责：
- 通过 WebSocket 向前端推送实时告警
- 记录告警历史供前端查询
- 可扩展：邮件、短信等通知渠道

核心接口：
- notify(alert_event: AlertEvent) -> None
- broadcast_websocket(message: dict) -> None

被调用方：
- monitor.py 触发告警时调用
"""
