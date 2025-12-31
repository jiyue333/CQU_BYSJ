"""媒体网关适配层

抽象接口定义和 ZLMediaKit 实现。
隔离网关差异，Stream Manager 内部统一调用 GatewayAdapter。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

import aiohttp

from app.core.config import settings


@dataclass
class StreamInfo:
    """流信息"""
    stream_id: str
    play_url: str                    # 浏览器播放地址（HTTP-FLV）
    rtsp_url: Optional[str] = None   # RTSP 播放地址
    hls_url: Optional[str] = None    # HLS 播放地址
    webrtc_url: Optional[str] = None # WebRTC 播放地址


@dataclass
class PublishInfo:
    """浏览器摄像头推流所需信息"""
    whip_url: str                    # WHIP 推流地址
    token: str                       # 短期有效 token
    expires_at: int                  # 过期时间戳
    ice_servers: list                # STUN/TURN 服务器列表


class GatewayAdapter(ABC):
    """媒体网关适配层抽象接口"""
    
    @abstractmethod
    async def create_rtsp_proxy(
        self, 
        stream_id: str, 
        rtsp_url: str,
        retry_count: int = 3,
        timeout_sec: int = 10
    ) -> StreamInfo:
        """创建 RTSP 拉流代理"""
        pass
    
    @abstractmethod
    async def create_file_stream(
        self, 
        stream_id: str, 
        file_path: str,
        realtime: bool = True
    ) -> StreamInfo:
        """创建文件转流"""
        pass
    
    @abstractmethod
    async def create_webcam_ingest(
        self, 
        stream_id: str
    ) -> tuple[StreamInfo, PublishInfo]:
        """创建浏览器摄像头推流会话"""
        pass
    
    @abstractmethod
    async def delete_stream(self, stream_id: str) -> bool:
        """删除流"""
        pass
    
    @abstractmethod
    async def get_snapshot(
        self, 
        stream_id: str, 
        timeout_sec: float = 2.0,
        expire_sec: int = 1
    ) -> Optional[bytes]:
        """获取快照（JPEG bytes）"""
        pass
    
    @abstractmethod
    async def get_stream_info(self, stream_id: str) -> Optional[StreamInfo]:
        """获取流信息"""
        pass


class ZLMediaKitAdapter(GatewayAdapter):
    """ZLMediaKit 适配器实现"""
    
    def __init__(
        self, 
        base_url: str = settings.zlm_base_url,
        secret: str = settings.zlm_secret
    ):
        self.base_url = base_url.rstrip("/")
        self.secret = secret
        self.app = "live"  # ZLMediaKit 应用名
        self.vhost = "__defaultVhost__"
    
    async def _call_api(
        self, 
        path: str, 
        params: dict,
        timeout: float = 10.0
    ) -> dict:
        """调用 ZLMediaKit API"""
        url = f"{self.base_url}{path}"
        params["secret"] = self.secret
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, 
                params=params, 
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as resp:
                if resp.status != 200:
                    raise Exception(f"ZLMediaKit API error: {resp.status}")
                data = await resp.json()
                if data.get("code") != 0:
                    raise Exception(f"ZLMediaKit API error: {data.get('msg', 'Unknown error')}")
                return data
    
    def _build_play_urls(self, stream_id: str) -> StreamInfo:
        """构建播放地址"""
        return StreamInfo(
            stream_id=stream_id,
            play_url=f"{self.base_url}/{self.app}/{stream_id}.live.flv",
            hls_url=f"{self.base_url}/{self.app}/{stream_id}/hls.m3u8",
            rtsp_url=f"rtsp://{self.base_url.replace('http://', '').replace('https://', '').split(':')[0]}:{settings.zlm_rtsp_port}/{self.app}/{stream_id}",
            webrtc_url=f"{self.base_url}/index/api/webrtc?app={self.app}&stream={stream_id}&type=play"
        )
    
    async def create_rtsp_proxy(
        self, 
        stream_id: str, 
        rtsp_url: str,
        retry_count: int = 3,
        timeout_sec: int = 10
    ) -> StreamInfo:
        """调用 ZLMediaKit addStreamProxy API 创建 RTSP 拉流代理"""
        await self._call_api("/index/api/addStreamProxy", {
            "vhost": self.vhost,
            "app": self.app,
            "stream": stream_id,
            "url": rtsp_url,
            "retry_count": retry_count,
            "timeout_sec": timeout_sec,
            "enable_hls": 1,
            "enable_mp4": 0,
            "enable_rtsp": 1,
            "enable_rtmp": 1,
            "enable_ts": 0,
            "enable_fmp4": 0,
        })
        return self._build_play_urls(stream_id)

    async def create_file_stream(
        self, 
        stream_id: str, 
        file_path: str,
        realtime: bool = True
    ) -> StreamInfo:
        """调用 ZLMediaKit addFFmpegSource API 创建文件转流"""
        # FFmpeg 参数：-re 表示按实时节奏输出，-stream_loop -1 表示循环播放
        ffmpeg_cmd_send = ""
        if realtime:
            ffmpeg_cmd_send = "-re"
        
        await self._call_api("/index/api/addFFmpegSource", {
            "vhost": self.vhost,
            "app": self.app,
            "stream": stream_id,
            "src_url": file_path,
            "dst_url": f"rtmp://127.0.0.1/{self.app}/{stream_id}",
            "timeout_ms": 10000,
            "enable_hls": 1,
            "enable_mp4": 0,
            "ffmpeg_cmd_key": ffmpeg_cmd_send,
        })
        return self._build_play_urls(stream_id)
    
    async def create_webcam_ingest(
        self, 
        stream_id: str
    ) -> tuple[StreamInfo, PublishInfo]:
        """创建浏览器摄像头推流会话
        
        ZLMediaKit 支持 WebRTC 推流（WHIP 协议）
        """
        import time
        import secrets
        
        # 生成短期有效 token
        token = secrets.token_urlsafe(32)
        expires_at = int(time.time()) + 300  # 5 分钟有效期
        
        stream_info = self._build_play_urls(stream_id)
        
        publish_info = PublishInfo(
            whip_url=f"{self.base_url}/index/api/webrtc?app={self.app}&stream={stream_id}&type=push",
            token=token,
            expires_at=expires_at,
            ice_servers=[
                {"urls": ["stun:stun.l.google.com:19302"]}
            ]
        )
        
        return stream_info, publish_info
    
    async def delete_stream(self, stream_id: str) -> bool:
        """删除流"""
        try:
            # 尝试删除代理流
            await self._call_api("/index/api/delStreamProxy", {
                "key": f"{self.vhost}/{self.app}/{stream_id}"
            })
            return True
        except Exception:
            try:
                # 尝试关闭流
                await self._call_api("/index/api/close_streams", {
                    "vhost": self.vhost,
                    "app": self.app,
                    "stream": stream_id,
                    "force": 1
                })
                return True
            except Exception:
                return False
    
    async def get_snapshot(
        self, 
        stream_id: str, 
        timeout_sec: float = 2.0,
        expire_sec: int = 1
    ) -> Optional[bytes]:
        """调用 ZLMediaKit getSnap API 获取快照"""
        url = f"{self.base_url}/index/api/getSnap"
        params = {
            "secret": self.secret,
            "url": f"rtsp://127.0.0.1/{self.app}/{stream_id}",
            "timeout_sec": timeout_sec,
            "expire_sec": expire_sec
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, 
                    params=params, 
                    timeout=aiohttp.ClientTimeout(total=timeout_sec + 1)
                ) as resp:
                    if resp.status == 200 and resp.content_type == "image/jpeg":
                        return await resp.read()
        except Exception:
            pass
        return None
    
    async def get_stream_info(self, stream_id: str) -> Optional[StreamInfo]:
        """获取流信息"""
        try:
            data = await self._call_api("/index/api/getMediaList", {
                "vhost": self.vhost,
                "app": self.app,
                "stream": stream_id
            })
            if data.get("data"):
                return self._build_play_urls(stream_id)
        except Exception:
            pass
        return None


# 全局网关适配器实例
_gateway_adapter: Optional[GatewayAdapter] = None


def get_gateway_adapter() -> GatewayAdapter:
    """获取网关适配器（单例）"""
    global _gateway_adapter
    if _gateway_adapter is None:
        _gateway_adapter = ZLMediaKitAdapter()
    return _gateway_adapter
