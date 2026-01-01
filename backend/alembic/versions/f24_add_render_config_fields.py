"""F-24: Add render config fields to system_configs

方案 F 扩展：新增渲染相关配置字段
- render_fps: 渲染输出帧率
- render_infer_stride: 推理步长
- render_overlay_alpha: 热力图叠加透明度

Revision ID: f24_render_config
Revises: e7dda82d070c
Create Date: 2026-01-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f24_render_config'
down_revision: Union[str, None] = 'e7dda82d070c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """添加渲染配置字段"""
    # 添加 render_fps 字段
    op.add_column(
        'system_configs',
        sa.Column(
            'render_fps',
            sa.Integer(),
            nullable=False,
            server_default='24',
            comment='渲染输出帧率 (1-60)'
        )
    )
    
    # 添加 render_infer_stride 字段
    op.add_column(
        'system_configs',
        sa.Column(
            'render_infer_stride',
            sa.Integer(),
            nullable=False,
            server_default='3',
            comment='推理步长，每 N 帧推理一次 (1-10)'
        )
    )
    
    # 添加 render_overlay_alpha 字段
    op.add_column(
        'system_configs',
        sa.Column(
            'render_overlay_alpha',
            sa.Float(),
            nullable=False,
            server_default='0.4',
            comment='热力图叠加透明度 (0-1)'
        )
    )


def downgrade() -> None:
    """移除渲染配置字段"""
    op.drop_column('system_configs', 'render_overlay_alpha')
    op.drop_column('system_configs', 'render_infer_stride')
    op.drop_column('system_configs', 'render_fps')
