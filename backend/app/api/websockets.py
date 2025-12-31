"""WebSocket 端点

提供检测结果和状态变更的实时推送。
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.result_push_service import get_result_push_service
from app.services.status_push_service import get_status_push_service

router = APIRouter()


@router.websocket("/result/{stream_id}")
async def websocket_result(websocket: WebSocket, stream_id: str):
    """订阅某路视频的检测结果推送
    
    协议：
    - 客户端发送 {"type": "ping", "ts": timestamp} 进行心跳
    - 服务端回复 {"type": "pong", "ts": timestamp}
    - 客户端发送 {"type": "recover", "last_id": "xxx"} 请求断点续传
    - 服务端推送 {"type": "result", "msg_id": "xxx", "data": {...}}
    - 服务端推送 {"type": "recovery", "msg_id": "xxx", "data": {...}} 恢复消息
    - 服务端推送 {"type": "recovery_complete", "count": n} 恢复完成
    """
    service = get_result_push_service()
    await service.subscribe(websocket, stream_id)


@router.websocket("/status")
async def websocket_status(websocket: WebSocket):
    """订阅所有视频流的状态变更
    
    协议：
    - 客户端发送 {"type": "ping", "ts": timestamp} 进行心跳
    - 服务端回复 {"type": "pong", "ts": timestamp}
    - 服务端推送 {"type": "status", "data": {"stream_id": "xxx", "status": "xxx", ...}}
    """
    service = get_status_push_service()
    await service.subscribe(websocket)
