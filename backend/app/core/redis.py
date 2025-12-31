"""Redis 配置"""

from typing import Optional

import redis.asyncio as redis

from app.core.config import settings

_redis_client: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    """获取 Redis 客户端（单例模式）"""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=50,  # 连接池最大连接数
            socket_connect_timeout=5,  # 连接超时（秒）
            socket_keepalive=True,  # 启用 TCP keepalive
            health_check_interval=30,  # 健康检查间隔（秒）
        )
    return _redis_client


async def init_redis() -> None:
    """初始化 Redis 连接"""
    await get_redis()


async def close_redis() -> None:
    """关闭 Redis 连接"""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None


async def check_redis_connection() -> bool:
    """检查 Redis 连接是否正常"""
    try:
        client = await get_redis()
        await client.ping()
        return True
    except Exception as e:
        print(f"Redis connection failed: {e}")
        return False
