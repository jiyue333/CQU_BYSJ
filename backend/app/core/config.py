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
        env_file=str(_PROJECT_ROOT / ".env"),
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
    YOLO_MODEL_PATH: str = str(_PROJECT_ROOT / "yolo11n.pt")
    YOLO_CONF_THRESHOLD: float = 0.5
    YOLO_DEVICE: str = "cpu"  # cpu / cuda / mps
    YOLO_CLASSES: str = "0"  # 检测类别，逗号分隔，如 "0" 或 "0,1"

    # WebSocket 配置
    WS_HEARTBEAT_INTERVAL: int = 30  # 秒

    # 告警配置
    # 注意：告警阈值现在通过前端在每个区域（Region）中单独配置
    ALERT_COOLDOWN_SECONDS: int = 30  # 同一区域告警冷却时间（秒）

    # DM-Count 密度图配置
    DMCOUNT_MODEL_NAME: str = "DM-Count"
    DMCOUNT_MODEL_WEIGHTS: str = "QNRF"  # SHA / SHB / QNRF — QNRF 场景多样性最好
    DMCOUNT_INTERVAL_SEC: float = 1.0  # DM-Count 运行间隔（秒），同时控制画面推送频率

    # 推理流水线配置
    # YOLO: 每帧都跑（追踪+计数），不参与画面渲染
    # DM-Count: 按 DMCOUNT_INTERVAL_SEC 间隔运行，负责密度估计+热力图渲染+画面推送
    WS_PUSH_FPS: int = 0  # WebSocket 推送帧率上限，0=跟随 DM-Count 间隔

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
