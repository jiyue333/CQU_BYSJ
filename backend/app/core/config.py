"""
应用配置

使用 pydantic-settings 管理配置，支持环境变量覆盖
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 应用信息
    APP_NAME: str = "CrowdFlow"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # 数据库配置
    DATABASE_URL: str = "sqlite:///./data/app.db"

    # 文件路径配置
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent
    UPLOAD_DIR: Path = BASE_DIR / "uploads" / "videos"
    MODEL_DIR: Path = BASE_DIR / "models"
    DATA_DIR: Path = BASE_DIR / "data"

    # YOLO 模型配置
    YOLO_MODEL_PATH: str = "yolov8n.pt"
    YOLO_CONF_THRESHOLD: float = 0.5
    YOLO_DEVICE: str = "cpu"  # cpu / cuda / mps

    # WebSocket 配置
    WS_HEARTBEAT_INTERVAL: int = 30  # 秒

    # 告警默认配置
    ALERT_TOTAL_WARNING: int = 50
    ALERT_TOTAL_CRITICAL: int = 100
    ALERT_COOLDOWN_SECONDS: int = 30

    def ensure_dirs(self) -> None:
        """确保必要的目录存在"""
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        self.MODEL_DIR.mkdir(parents=True, exist_ok=True)
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)


# 全局配置实例
settings = Settings()
