"""应用配置"""

from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # 应用配置
    app_name: str = "crowd-counting"
    debug: bool = False

    # 数据库配置
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/crowd_counting"

    # Redis 配置
    redis_url: str = "redis://localhost:6379/0"

    # Redis Streams 配置
    stream_result_maxlen: int = 500  # 结果 Stream 最大长度（近似裁剪）
    stream_status_maxlen: int = 1000  # 状态 Stream 最大长度（近似裁剪）
    stream_read_block_ms: int = 1000  # 阻塞读取超时（毫秒）
    stream_read_count: int = 100  # 每次读取最大消息数
    stream_recover_count: int = 50  # 断点续传最大恢复消息数

    # ZLMediaKit 配置
    zlm_base_url: str = "http://localhost:8080"
    zlm_secret: str = ""
    zlm_rtsp_port: int = 554
    zlm_http_port: int = 80

    # CORS 配置
    cors_origins: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    # 流管理配置
    max_concurrent_streams: int = 10
    auto_stop_delay: int = 60  # 无观看者自动停止延迟（秒）
    cooldown_duration: int = 60  # COOLDOWN 持续时间（秒）

    # 文件上传配置
    file_storage_path: str = "/data/uploads"
    file_max_size_mb: int = 500
    file_retention_days: int = 7
    file_allowed_extensions: List[str] = ["mp4", "avi", "mkv", "mov", "webm", "flv"]

    # WebSocket 配置
    ws_heartbeat_interval: int = 30
    ws_heartbeat_timeout: int = 10
    ws_slow_client_threshold: int = 5

    # 推理配置
    inference_fps: int = 2
    confidence_threshold: float = 0.5
    heatmap_grid_size: int = 20
    heatmap_decay: float = 0.3

    # getSnap 配置
    snap_timeout_sec: float = 2.0
    snap_max_failures: int = 5
    snap_backoff_base: float = 1.0
    snap_backoff_max: float = 30.0


settings = Settings()
