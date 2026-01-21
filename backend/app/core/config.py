"""
应用配置

使用 pydantic-settings 管理配置，支持环境变量覆盖
"""

from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


# 项目根目录（backend 的上一级）
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


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

    # 文件路径配置（可通过 .env 覆盖，使用字符串类型）
    BASE_DIR: str = str(_PROJECT_ROOT)
    DATA_DIR: str = str(_PROJECT_ROOT / "data")
    UPLOAD_DIR: str = str(_PROJECT_ROOT / "uploads" / "videos")
    MODEL_DIR: str = str(_PROJECT_ROOT / "models")
    LOGS_DIR: str = str(_PROJECT_ROOT / "logs")

    # 数据库配置
    DATABASE_URL: Optional[str] = None  # 可在 .env 中直接设置完整 URL

    # YOLO 模型配置
    YOLO_MODEL_PATH: str = "yolov8n.pt"
    YOLO_CONF_THRESHOLD: float = 0.5
    YOLO_DEVICE: str = "cpu"  # cpu / cuda / mps

    # WebSocket 配置
    WS_HEARTBEAT_INTERVAL: int = 30  # 秒

    # 告警配置
    # 注意：告警阈值现在通过前端在每个区域（Region）中单独配置
    ALERT_COOLDOWN_SECONDS: int = 30  # 同一区域告警冷却时间（秒）

    # 密度计算配置
    # 密度 = 人数 × DENSITY_FACTOR / 面积（像素²）
    # 默认 10000，使得 100 人 / 10000 像素² ≈ 1.0
    DENSITY_FACTOR: float = 10000.0
    DENSITY_MAX: float = 100.0  # 密度上限

    def get_database_url(self) -> str:
        """获取数据库 URL"""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"sqlite:///{self.DATA_DIR}/app.db"

    def ensure_dirs(self) -> None:
        """确保必要的目录存在"""
        Path(self.DATA_DIR).mkdir(parents=True, exist_ok=True)
        Path(self.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
        Path(self.MODEL_DIR).mkdir(parents=True, exist_ok=True)
        Path(self.LOGS_DIR).mkdir(parents=True, exist_ok=True)


# 全局配置实例
settings = Settings()
