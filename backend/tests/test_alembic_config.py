"""测试 Alembic 配置"""

import pytest
from pathlib import Path
from alembic.config import Config
from alembic.script import ScriptDirectory


def test_alembic_config_exists():
    """测试 Alembic 配置文件存在"""
    backend_dir = Path(__file__).parent.parent
    alembic_ini = backend_dir / "alembic.ini"
    assert alembic_ini.exists(), "alembic.ini 文件不存在"


def test_alembic_env_exists():
    """测试 Alembic env.py 存在"""
    backend_dir = Path(__file__).parent.parent
    env_py = backend_dir / "alembic" / "env.py"
    assert env_py.exists(), "alembic/env.py 文件不存在"


def test_alembic_versions_dir_exists():
    """测试 Alembic versions 目录存在"""
    backend_dir = Path(__file__).parent.parent
    versions_dir = backend_dir / "alembic" / "versions"
    assert versions_dir.exists(), "alembic/versions 目录不存在"
    assert versions_dir.is_dir(), "alembic/versions 不是目录"


def test_alembic_config_loads():
    """测试 Alembic 配置可以加载"""
    backend_dir = Path(__file__).parent.parent
    alembic_ini = str(backend_dir / "alembic.ini")
    
    config = Config(alembic_ini)
    assert config is not None, "无法加载 Alembic 配置"
    
    # 检查关键配置项
    script_location = config.get_main_option("script_location")
    assert script_location is not None, "script_location 未配置"


def test_alembic_script_directory():
    """测试 Alembic ScriptDirectory 可以初始化"""
    backend_dir = Path(__file__).parent.parent
    alembic_ini = str(backend_dir / "alembic.ini")
    
    config = Config(alembic_ini)
    script = ScriptDirectory.from_config(config)
    
    assert script is not None, "无法初始化 ScriptDirectory"
    assert script.dir is not None, "ScriptDirectory.dir 为空"


def test_alembic_env_imports():
    """测试 Alembic env.py 可以导入必要的模块"""
    # 这个测试确保 env.py 中的导入不会失败
    try:
        from app.core.config import settings
        from app.core.database import Base
        
        assert settings is not None, "无法导入 settings"
        assert Base is not None, "无法导入 Base"
    except ImportError as e:
        pytest.fail(f"导入失败: {e}")


def test_database_url_configured():
    """测试数据库 URL 已配置"""
    from app.core.config import settings
    
    assert settings.database_url is not None, "DATABASE_URL 未配置"
    assert "postgresql" in settings.database_url, "DATABASE_URL 不是 PostgreSQL"
    assert "asyncpg" in settings.database_url, "DATABASE_URL 未使用 asyncpg 驱动"


@pytest.mark.asyncio
async def test_base_metadata_exists():
    """测试 Base.metadata 存在"""
    from app.core.database import Base
    
    assert Base.metadata is not None, "Base.metadata 不存在"
    # 注意：此时可能还没有模型注册，所以 tables 可能为空
    # 这是正常的，因为我们还没有创建模型文件
