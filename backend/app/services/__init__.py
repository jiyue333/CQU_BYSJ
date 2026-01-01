"""Services package.

导出所有服务类，便于统一导入。
方案 F：使用 RenderControlService 替代 InferenceControlService
"""

from app.services.gateway_adapter import (
    GatewayAdapter,
    ZLMediaKitAdapter,
    StreamInfo,
    PublishInfo,
    GatewayError,
    GatewayConnectionError,
    GatewayAPIError,
    get_gateway_adapter,
)
from app.services.render_control import (
    RenderControlService,
    get_render_control,
)
from app.services.stream_service import (
    StreamService,
    StreamServiceError,
    StreamNotFoundError,
    ConcurrentLimitError,
    InvalidStateTransitionError,
    get_stream_service,
)
from app.services.result_push_service import (
    ResultPushService,
    get_result_push_service,
)
from app.services.status_push_service import (
    StatusPushService,
    get_status_push_service,
)
from app.services.file_storage_service import (
    FileStorageService,
    FileStorageError,
    FileTooLargeError,
    InvalidFileTypeError,
    get_file_storage_service,
)

__all__ = [
    # Gateway Adapter
    "GatewayAdapter",
    "ZLMediaKitAdapter",
    "StreamInfo",
    "PublishInfo",
    "GatewayError",
    "GatewayConnectionError",
    "GatewayAPIError",
    "get_gateway_adapter",
    # Render Control (方案 F)
    "RenderControlService",
    "get_render_control",
    # Stream Service
    "StreamService",
    "StreamServiceError",
    "StreamNotFoundError",
    "ConcurrentLimitError",
    "InvalidStateTransitionError",
    "get_stream_service",
    # Result Push Service
    "ResultPushService",
    "get_result_push_service",
    # Status Push Service
    "StatusPushService",
    "get_status_push_service",
    # File Storage Service
    "FileStorageService",
    "FileStorageError",
    "FileTooLargeError",
    "InvalidFileTypeError",
    "get_file_storage_service",
]
