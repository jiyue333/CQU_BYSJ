"""Initial migration - create all tables

Revision ID: 3bdbc91b66d2
Revises: 
Create Date: 2025-12-31 16:52:17.897896

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '3bdbc91b66d2'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create enum types first with lowercase values (matching Python enum values)
    stream_type = postgresql.ENUM('file', 'webcam', 'rtsp', name='stream_type', create_type=False)
    stream_status = postgresql.ENUM('starting', 'running', 'stopped', 'error', 'cooldown', name='stream_status', create_type=False)
    stream_type.create(op.get_bind(), checkfirst=True)
    stream_status.create(op.get_bind(), checkfirst=True)
    
    op.create_table('video_streams',
    sa.Column('id', sa.String(length=36), nullable=False, comment='视频流唯一标识 (UUID)'),
    sa.Column('name', sa.String(length=255), nullable=False, comment='显示名称'),
    sa.Column('type', stream_type, nullable=False, comment='视频流类型'),
    sa.Column('status', stream_status, nullable=False, comment='当前状态'),
    sa.Column('play_url', sa.String(length=512), nullable=True, comment='播放地址'),
    sa.Column('source_url', sa.String(length=512), nullable=True, comment='RTSP 地址（仅 rtsp 类型）'),
    sa.Column('file_id', sa.String(length=36), nullable=True, comment='文件 ID（仅 file 类型）'),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='创建时间'),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='更新时间'),
    sa.CheckConstraint("(type != 'file') OR (file_id IS NOT NULL)", name='ck_video_streams_file_requires_file_id'),
    sa.CheckConstraint("(type != 'file') OR (source_url IS NULL)", name='ck_video_streams_file_no_source_url'),
    sa.CheckConstraint("(type != 'rtsp') OR (file_id IS NULL)", name='ck_video_streams_rtsp_no_file_id'),
    sa.CheckConstraint("(type != 'rtsp') OR (source_url IS NOT NULL)", name='ck_video_streams_rtsp_requires_source_url'),
    sa.CheckConstraint("(type != 'webcam') OR (file_id IS NULL AND source_url IS NULL)", name='ck_video_streams_webcam_no_file_or_source'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('history_stats',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False, comment='自增主键'),
    sa.Column('stream_id', sa.String(length=36), nullable=False, comment='关联的视频流 ID'),
    sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, comment='检测时间戳'),
    sa.Column('total_count', sa.Integer(), nullable=False, comment='总人数'),
    sa.Column('region_stats', postgresql.JSON(astext_type=sa.Text()), nullable=False, comment='各区域统计 [{region_id, count, density, level}, ...]'),
    sa.CheckConstraint('total_count >= 0', name='ck_history_stats_total_count_non_negative'),
    sa.ForeignKeyConstraint(['stream_id'], ['video_streams.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_history_stats_stream_id'), 'history_stats', ['stream_id'], unique=False)
    op.create_index('ix_history_stats_stream_timestamp', 'history_stats', ['stream_id', 'timestamp'], unique=False)
    op.create_index(op.f('ix_history_stats_timestamp'), 'history_stats', ['timestamp'], unique=False)
    op.create_table('rois',
    sa.Column('id', sa.String(length=36), nullable=False, comment='ROI 唯一标识 (UUID)'),
    sa.Column('stream_id', sa.String(length=36), nullable=False, comment='关联的视频流 ID'),
    sa.Column('name', sa.String(length=255), nullable=False, comment='区域名称'),
    sa.Column('points', postgresql.JSON(astext_type=sa.Text()), nullable=False, comment='多边形顶点列表 [{x, y}, ...]'),
    sa.Column('density_thresholds', postgresql.JSON(astext_type=sa.Text()), nullable=False, comment='密度阈值配置 {low, medium, high}'),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='创建时间'),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='更新时间'),
    sa.ForeignKeyConstraint(['stream_id'], ['video_streams.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_rois_stream_id'), 'rois', ['stream_id'], unique=False)
    op.create_table('system_configs',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False, comment='自增主键'),
    sa.Column('stream_id', sa.String(length=36), nullable=False, comment='关联的视频流 ID'),
    sa.Column('confidence_threshold', sa.Float(), nullable=False, comment='检测置信度阈值 (0-1)'),
    sa.Column('inference_fps', sa.Integer(), nullable=False, comment='推理频率 (1-3)'),
    sa.Column('heatmap_grid_size', sa.Integer(), nullable=False, comment='热力图网格大小'),
    sa.Column('heatmap_decay', sa.Float(), nullable=False, comment='热力图衰减因子（EMA alpha）'),
    sa.ForeignKeyConstraint(['stream_id'], ['video_streams.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_system_configs_stream_id'), 'system_configs', ['stream_id'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_system_configs_stream_id'), table_name='system_configs')
    op.drop_table('system_configs')
    op.drop_index(op.f('ix_rois_stream_id'), table_name='rois')
    op.drop_table('rois')
    op.drop_index(op.f('ix_history_stats_timestamp'), table_name='history_stats')
    op.drop_index('ix_history_stats_stream_timestamp', table_name='history_stats')
    op.drop_index(op.f('ix_history_stats_stream_id'), table_name='history_stats')
    op.drop_table('history_stats')
    op.drop_table('video_streams')
    
    # Drop enum types
    stream_type = postgresql.ENUM('file', 'webcam', 'rtsp', name='stream_type')
    stream_status = postgresql.ENUM('starting', 'running', 'stopped', 'error', 'cooldown', name='stream_status')
    stream_type.drop(op.get_bind(), checkfirst=True)
    stream_status.drop(op.get_bind(), checkfirst=True)
