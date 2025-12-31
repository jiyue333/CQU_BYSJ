"""Media Gateway Adapter Layer

Abstract interface and ZLMediaKit implementation.
Isolates gateway differences, Stream Manager calls GatewayAdapter uniformly.
"""

import logging
import secrets
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse

import aiohttp

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class StreamInfo:
    """Stream information with all protocol URLs."""
    stream_id: str
    play_url: str
    rtsp_url: Optional[str] = None
    hls_url: Optional[str] = None
    webrtc_url: Optional[str] = None


@dataclass
class PublishInfo:
    """Browser webcam publish info for WebRTC WHIP protocol."""
    whip_url: str
    token: str
    expires_at: int
    ice_servers: list = field(default_factory=list)


class GatewayError(Exception):
    """Base gateway error."""
    pass


class GatewayConnectionError(GatewayError):
    """Gateway connection error."""
    pass


class GatewayAPIError(GatewayError):
    """Gateway API call error."""
    def __init__(self, message: str, code: int = -1):
        super().__init__(message)
        self.code = code


class GatewayAdapter(ABC):
    """Abstract media gateway adapter interface."""
    
    @abstractmethod
    async def create_rtsp_proxy(
        self, stream_id: str, rtsp_url: str,
        retry_count: int = 3, timeout_sec: int = 10
    ) -> StreamInfo:
        """Create RTSP pull proxy."""
        pass
    
    @abstractmethod
    async def create_file_stream(
        self, stream_id: str, file_path: str,
        realtime: bool = True, loop: bool = True
    ) -> StreamInfo:
        """Create file stream."""
        pass
    
    @abstractmethod
    async def create_webcam_ingest(self, stream_id: str) -> tuple[StreamInfo, PublishInfo]:
        """Create webcam ingest session."""
        pass
    
    @abstractmethod
    async def delete_stream(self, stream_id: str) -> bool:
        """Delete stream."""
        pass
    
    @abstractmethod
    async def get_snapshot(
        self, stream_id: str, timeout_sec: float = 2.0, expire_sec: int = 1
    ) -> Optional[bytes]:
        """Get snapshot (JPEG bytes)."""
        pass
    
    @abstractmethod
    async def get_stream_info(self, stream_id: str) -> Optional[StreamInfo]:
        """Get stream info."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Health check."""
        pass


class ZLMediaKitAdapter(GatewayAdapter):
    """ZLMediaKit adapter implementation."""
    
    def __init__(
        self, 
        base_url: str = settings.zlm_base_url,
        secret: str = settings.zlm_secret,
        rtsp_port: int = settings.zlm_rtsp_port
    ):
        self.base_url = base_url.rstrip("/")
        self.secret = secret
        self.rtsp_port = rtsp_port
        self.app = "live"
        self.vhost = "__defaultVhost__"
        parsed = urlparse(self.base_url)
        self.host = parsed.hostname or "localhost"
        logger.info(f"ZLMediaKitAdapter initialized: base_url={self.base_url}")
    
    async def _call_api(self, path: str, params: dict, timeout: float = 10.0) -> dict:
        """Call ZLMediaKit API."""
        url = f"{self.base_url}{path}"
        params["secret"] = self.secret
        logger.debug(f"Calling ZLMediaKit API: {path}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, params=params,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as resp:
                    if resp.status != 200:
                        raise GatewayConnectionError(f"HTTP error: {resp.status}")
                    data = await resp.json()
                    if data.get("code") != 0:
                        raise GatewayAPIError(data.get("msg", "Unknown error"), data.get("code", -1))
                    return data
        except aiohttp.ClientError as e:
            raise GatewayConnectionError(f"Connection failed: {e}") from e
    
    def _build_play_urls(self, stream_id: str) -> StreamInfo:
        """Build play URLs for all protocols."""
        return StreamInfo(
            stream_id=stream_id,
            play_url=f"{self.base_url}/{self.app}/{stream_id}.live.flv",
            hls_url=f"{self.base_url}/{self.app}/{stream_id}/hls.m3u8",
            rtsp_url=f"rtsp://{self.host}:{self.rtsp_port}/{self.app}/{stream_id}",
            webrtc_url=f"{self.base_url}/index/api/webrtc?app={self.app}&stream={stream_id}&type=play"
        )


    async def create_rtsp_proxy(
        self, stream_id: str, rtsp_url: str,
        retry_count: int = 3, timeout_sec: int = 10
    ) -> StreamInfo:
        """Create RTSP pull proxy via addStreamProxy API."""
        logger.info(f"Creating RTSP proxy: stream_id={stream_id}")
        await self._call_api("/index/api/addStreamProxy", {
            "vhost": self.vhost, "app": self.app, "stream": stream_id,
            "url": rtsp_url, "retry_count": retry_count, "timeout_sec": timeout_sec,
            "enable_hls": 1, "enable_mp4": 0, "enable_rtsp": 1, "enable_rtmp": 1,
        })
        return self._build_play_urls(stream_id)

    async def create_file_stream(
        self, stream_id: str, file_path: str,
        realtime: bool = True, loop: bool = True
    ) -> StreamInfo:
        """Create file stream via addFFmpegSource API."""
        logger.info(f"Creating file stream: stream_id={stream_id}, file_path={file_path}")
        ffmpeg_cmd_key = ""
        if realtime:
            ffmpeg_cmd_key = "-re"
        if loop:
            ffmpeg_cmd_key = f"{ffmpeg_cmd_key} -stream_loop -1" if ffmpeg_cmd_key else "-stream_loop -1"
        
        dst_url = f"rtmp://127.0.0.1/{self.app}/{stream_id}"
        await self._call_api("/index/api/addFFmpegSource", {
            "vhost": self.vhost, "app": self.app, "stream": stream_id,
            "src_url": file_path, "dst_url": dst_url, "timeout_ms": 10000,
            "enable_hls": 1, "enable_mp4": 0, "ffmpeg_cmd_key": ffmpeg_cmd_key.strip(),
        })
        return self._build_play_urls(stream_id)
    
    async def create_webcam_ingest(self, stream_id: str) -> tuple[StreamInfo, PublishInfo]:
        """Create webcam ingest session."""
        logger.info(f"Creating webcam ingest: stream_id={stream_id}")
        token = secrets.token_urlsafe(32)
        expires_at = int(time.time()) + 300
        stream_info = self._build_play_urls(stream_id)
        publish_info = PublishInfo(
            whip_url=f"{self.base_url}/index/api/webrtc?app={self.app}&stream={stream_id}&type=push",
            token=token, expires_at=expires_at,
            ice_servers=[{"urls": ["stun:stun.l.google.com:19302"]}]
        )
        return stream_info, publish_info


    async def delete_stream(self, stream_id: str) -> bool:
        """Delete stream."""
        logger.info(f"Deleting stream: stream_id={stream_id}")
        stream_key = f"{self.vhost}/{self.app}/{stream_id}"
        
        try:
            await self._call_api("/index/api/delStreamProxy", {"key": stream_key})
            return True
        except GatewayAPIError:
            pass
        
        try:
            await self._call_api("/index/api/delFFmpegSource", {"key": stream_key})
            return True
        except GatewayAPIError:
            pass
        
        try:
            await self._call_api("/index/api/close_streams", {
                "vhost": self.vhost, "app": self.app, "stream": stream_id, "force": 1
            })
            return True
        except GatewayAPIError:
            return False
    
    async def get_snapshot(
        self, stream_id: str, timeout_sec: float = 2.0, expire_sec: int = 1
    ) -> Optional[bytes]:
        """Get snapshot via getSnap API."""
        url = f"{self.base_url}/index/api/getSnap"
        params = {
            "secret": self.secret,
            "url": f"rtsp://127.0.0.1/{self.app}/{stream_id}",
            "timeout_sec": timeout_sec, "expire_sec": expire_sec
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, params=params,
                    timeout=aiohttp.ClientTimeout(total=timeout_sec + 1)
                ) as resp:
                    if resp.status == 200 and "image/jpeg" in (resp.content_type or ""):
                        return await resp.read()
        except Exception as e:
            logger.warning(f"Snapshot failed: {e}")
        return None
    
    async def get_stream_info(self, stream_id: str) -> Optional[StreamInfo]:
        """Get stream info via getMediaList API."""
        try:
            data = await self._call_api("/index/api/getMediaList", {
                "vhost": self.vhost, "app": self.app, "stream": stream_id
            })
            if data.get("data"):
                return self._build_play_urls(stream_id)
        except GatewayAPIError:
            pass
        return None
    
    async def health_check(self) -> bool:
        """Health check via getServerConfig API."""
        try:
            await self._call_api("/index/api/getServerConfig", {}, timeout=5.0)
            return True
        except Exception:
            return False


_gateway_adapter: Optional[GatewayAdapter] = None


def get_gateway_adapter() -> GatewayAdapter:
    """Get gateway adapter (singleton)."""
    global _gateway_adapter
    if _gateway_adapter is None:
        _gateway_adapter = ZLMediaKitAdapter()
    return _gateway_adapter


def reset_gateway_adapter() -> None:
    """Reset gateway adapter (for testing)."""
    global _gateway_adapter
    _gateway_adapter = None
