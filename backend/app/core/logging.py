"""日志配置

提供结构化日志支持，包括：
- JSON 格式日志（生产环境）
- 控制台彩色日志（开发环境）
- 错误日志记录工具
- 上下文绑定

Requirements: 9.3
"""

import logging
import sys
from typing import Any, Optional

import structlog
from structlog.types import Processor

from app.core.config import settings


def setup_logging() -> None:
    """配置结构化日志
    
    根据配置选择 JSON 或控制台格式输出。
    """
    # 确定日志级别
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    
    # 共享处理器
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
    ]
    
    # 根据配置选择渲染器
    if settings.log_format == "json" and not sys.stderr.isatty():
        # 生产环境：JSON 格式
        renderer: Processor = structlog.processors.JSONRenderer()
    else:
        # 开发环境：彩色控制台
        renderer = structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty())
    
    structlog.configure(
        processors=shared_processors + [renderer],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # 配置标准库日志
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """获取 logger
    
    Args:
        name: logger 名称，通常使用 __name__
        
    Returns:
        绑定的 logger 实例
    """
    return structlog.get_logger(name)


def bind_context(**kwargs: Any) -> None:
    """绑定上下文变量到当前日志
    
    绑定的变量会自动添加到后续的日志输出中。
    
    Args:
        **kwargs: 要绑定的键值对
    """
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_context() -> None:
    """清除所有绑定的上下文变量"""
    structlog.contextvars.clear_contextvars()


def unbind_context(*keys: str) -> None:
    """解绑指定的上下文变量
    
    Args:
        *keys: 要解绑的键名
    """
    structlog.contextvars.unbind_contextvars(*keys)


class LogContext:
    """日志上下文管理器
    
    用于在特定代码块中绑定上下文变量。
    
    Example:
        with LogContext(stream_id="abc123", operation="start"):
            logger.info("Starting stream")
            # 日志会自动包含 stream_id 和 operation
    """
    
    def __init__(self, **kwargs: Any):
        self._context = kwargs
        self._previous: dict[str, Any] = {}
    
    def __enter__(self) -> "LogContext":
        # 保存当前上下文
        current = structlog.contextvars.get_contextvars()
        for key in self._context:
            if key in current:
                self._previous[key] = current[key]
        
        # 绑定新上下文
        bind_context(**self._context)
        return self
    
    def __exit__(self, *args: Any) -> None:
        # 解绑添加的上下文
        unbind_context(*self._context.keys())
        
        # 恢复之前的值
        if self._previous:
            bind_context(**self._previous)


def log_error(
    logger: structlog.stdlib.BoundLogger,
    message: str,
    error: Optional[Exception] = None,
    **kwargs: Any
) -> None:
    """记录错误日志
    
    统一的错误日志记录方法，自动提取异常信息。
    
    Args:
        logger: logger 实例
        message: 错误消息
        error: 异常对象（可选）
        **kwargs: 额外的上下文信息
    """
    if error:
        kwargs["error_type"] = type(error).__name__
        kwargs["error_message"] = str(error)
    
    logger.error(message, **kwargs)


def log_warning(
    logger: structlog.stdlib.BoundLogger,
    message: str,
    **kwargs: Any
) -> None:
    """记录警告日志
    
    Args:
        logger: logger 实例
        message: 警告消息
        **kwargs: 额外的上下文信息
    """
    logger.warning(message, **kwargs)


def log_info(
    logger: structlog.stdlib.BoundLogger,
    message: str,
    **kwargs: Any
) -> None:
    """记录信息日志
    
    Args:
        logger: logger 实例
        message: 信息消息
        **kwargs: 额外的上下文信息
    """
    logger.info(message, **kwargs)

