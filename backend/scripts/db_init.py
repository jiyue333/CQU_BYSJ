#!/usr/bin/env python3
"""数据库初始化脚本

用于开发环境快速初始化数据库。
生产环境应使用 Alembic 迁移。
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import check_db_connection, init_db
from app.core.redis import check_redis_connection


async def main():
    """主函数"""
    print("=" * 60)
    print("数据库初始化脚本")
    print("=" * 60)
    
    # 检查数据库连接
    print("\n1. 检查数据库连接...")
    if await check_db_connection():
        print("   ✓ 数据库连接成功")
    else:
        print("   ✗ 数据库连接失败")
        print("\n请检查:")
        print("  - PostgreSQL 服务是否已启动")
        print("  - .env 文件中的 DATABASE_URL 配置是否正确")
        print("  - 数据库是否已创建: createdb crowd_counting")
        return 1
    
    # 检查 Redis 连接
    print("\n2. 检查 Redis 连接...")
    if await check_redis_connection():
        print("   ✓ Redis 连接成功")
    else:
        print("   ✗ Redis 连接失败")
        print("\n请检查:")
        print("  - Redis 服务是否已启动")
        print("  - .env 文件中的 REDIS_URL 配置是否正确")
        return 1
    
    # 初始化数据库
    print("\n3. 初始化数据库表...")
    print("   注意: 此操作会创建所有表，但不会删除现有数据")
    
    try:
        await init_db()
        print("   ✓ 数据库表创建成功")
    except Exception as e:
        print(f"   ✗ 数据库表创建失败: {e}")
        return 1
    
    print("\n" + "=" * 60)
    print("数据库初始化完成!")
    print("=" * 60)
    print("\n提示:")
    print("  - 生产环境请使用 Alembic 迁移: alembic upgrade head")
    print("  - 查看迁移历史: alembic history")
    print("  - 生成新迁移: alembic revision --autogenerate -m '描述'")
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
