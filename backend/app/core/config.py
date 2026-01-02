"""应用配置"""

from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # 忽略额外的环境变量
    )

    # 应用配置
    app_name: str = "crowd-counting"
    debug: bool = False

    # 数据库配置
    database_url: str = "postgresql+asyncpg://crowd_user:crowd_pass_dev@localhost:5432/crowd_counting"

    # Redis 配置
    redis_url: str = "redis://localhost:6379/0"

    # Redis Streams 配置
    stream_result_maxlen: int = 500  # 结果 Stream 最大长度（近似裁剪）
    stream_status_maxlen: int = 1000  # 状态 Stream 最大长度（近似裁剪）
    stream_read_block_ms: int = 1000  # 阻塞读取超时（毫秒）
    stream_read_count: int = 100  # 每次读取最大消息数
    stream_recover_count: int = 50  # 断点续传最大恢复消息数
    
    # 渲染状态 Stream 配置（方案 F）
    render_status_maxlen: int = 1000  # 渲染状态 Stream 最大长度
    render_latest_result_ttl: int = 60  # latest_result key TTL（秒）
    render_cleanup_on_stop: bool = True  # 停止时是否清理缓存

    # ZLMediaKit 配置
    zlm_base_url: str = "http://localhost:8080"  # 内部访问地址（容器间通信）
    zlm_external_url: str = "http://localhost:8080"  # 外部访问地址（浏览器访问）
    zlm_secret: str = ""
    zlm_rtsp_port: int = 554
    zlm_rtmp_port: int = 1935
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
    heatmap_decay: float = 0.5  # EMA 平滑因子，提高到 0.5 加快衰减

    # 渲染配置（方案F：服务端渲染热力图，MVP 阶段仅 env）
    # 决策锁定：延迟 1-5s / 渲染 24fps / 推理 8fps；同步模式：严格对齐（推理帧同帧叠加，其余帧复用缓存 heatmap）
    render_fps: int = 24  # 渲染输出帧率
    render_infer_stride: int = 3  # 每 N 帧推理一次（24/3=8fps）
    render_overlay_alpha: float = 0.4  # 热力图叠加透明度
    render_max_concurrent: int = 2  # 最大并发渲染数
    render_ffmpeg_preset: str = "ultrafast"
    render_ffmpeg_tune: str = "zerolatency"

    # 告警与指标配置
    default_alert_cooldown_sec: int = 60
    metrics_push_interval_sec: int = 2

    # getSnap 配置
    snap_timeout_sec: float = 2.0
    snap_max_failures: int = 5
    snap_backoff_base: float = 1.0
    snap_backoff_max: float = 30.0

    # 重连配置
    reconnect_max_attempts: int = 5  # 最大重连次数
    reconnect_base_delay: float = 1.0  # 重连基础延迟（秒）
    reconnect_max_delay: float = 30.0  # 最大重连延迟（秒）
    reconnect_jitter: float = 0.2  # 重连抖动因子 (±20%)

    # 日志配置
    log_level: str = "INFO"
    log_format: str = "json"  # json 或 console


settings = Settings()
