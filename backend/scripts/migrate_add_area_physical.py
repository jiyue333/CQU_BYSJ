"""
数据库迁移脚本：为 regions 表添加 area_physical 字段

SQLite ALTER TABLE ADD COLUMN 是安全操作，不会影响已有数据。
同时将旧的 density 阈值置为 NULL（旧值在 0-100 无量纲体系，新体系为 人/m²）。
"""

import sqlite3
import sys
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = PROJECT_ROOT / "data" / "app.db"


def migrate():
    if not DB_PATH.exists():
        print(f"数据库文件不存在: {DB_PATH}")
        print("首次运行时 SQLAlchemy 会自动创建包含新字段的表，无需迁移。")
        return

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    try:
        # 检查 area_physical 列是否已存在
        cursor.execute("PRAGMA table_info(regions)")
        columns = [row[1] for row in cursor.fetchall()]

        if "area_physical" in columns:
            print("area_physical 列已存在，跳过迁移。")
        else:
            # 添加 area_physical 列
            cursor.execute("ALTER TABLE regions ADD COLUMN area_physical FLOAT")
            print("✓ 已添加 area_physical 列")

        # 将旧的密度阈值置为 NULL
        # 旧体系: 0-100 无量纲；新体系: 0-20 人/m²
        cursor.execute("""
            UPDATE regions
            SET density_warning = NULL, density_critical = NULL
            WHERE density_warning IS NOT NULL OR density_critical IS NOT NULL
        """)
        affected = cursor.rowcount
        if affected > 0:
            print(f"✓ 已重置 {affected} 个区域的密度阈值（旧值不兼容新的 人/m² 体系）")
        else:
            print("无需重置密度阈值。")

        conn.commit()
        print("迁移完成。")

    except Exception as e:
        conn.rollback()
        print(f"迁移失败: {e}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
