"""
历史数据与导出 API

处理历史趋势查询和数据导出
"""

import csv
import uuid
from datetime import datetime
from io import StringIO
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.core.config import settings
from app.core.logger import logger
from app.models import ExportTask
from app.repositories import StatsRepository, VideoSourceRepository, ExportTaskRepository
from app.schemas.common import ApiResponse
from app.schemas.history import CrossLineHistoryStats, HistorySeriesItem, HistoryResponse, RegionHistoryStats
from app.schemas.export import ExportResponse

router = APIRouter(tags=["历史与导出"])


@router.get("/history", response_model=ApiResponse[HistoryResponse])
async def get_history(
    source_id: str = Query(..., description="数据源 ID"),
    from_time: str = Query(..., alias="from", description="开始时间 (ISO 8601)"),
    to_time: str = Query(..., alias="to", description="结束时间 (ISO 8601)"),
    interval: str = Query(default="1m", description="聚合间隔: 1m / 5m / 1h"),
    region_id: Optional[str] = Query(default=None, description="区域 ID（可选，筛选指定区域）"),
    db: Session = Depends(get_db),
):
    """历史趋势查询"""
    # 验证数据源存在
    source_repo = VideoSourceRepository(db)
    if not source_repo.get_by_id(source_id):
        raise HTTPException(status_code=404, detail="数据源不存在")

    # 查询统计数据
    stats_repo = StatsRepository(db)
    # 根据 interval 确定 interval_type
    interval_type = interval  # 1m / 5m / 1h
    stats = stats_repo.get_by_time_range(
        source_id=source_id,
        interval_type=interval_type,
        time_from=from_time,
        time_to=to_time,
        region_id=region_id,
    )

    series = []
    for s in stats:
        # 构建区域统计
        regions_data = {}
        region_stats_dict = s.get_region_stats_dict()
        for region_id, r in region_stats_dict.items():
            regions_data[region_id] = RegionHistoryStats(
                total_count_avg=r.avg,
                total_count_max=r.max,
                total_count_min=r.min,
                total_density_avg=r.density_avg,
            )

        crosslines_data = {}
        crossline_stats_dict = s.get_crossline_stats_dict()
        for line_id, c in crossline_stats_dict.items():
            crosslines_data[line_id] = CrossLineHistoryStats(
                name=c.name,
                in_total=c.in_total,
                out_total=c.out_total,
            )

        series.append(
            HistorySeriesItem(
                time=s.time_bucket,
                total_count_avg=s.total_count_avg,
                total_count_max=s.total_count_max,
                total_count_min=s.total_count_min,
                total_density_avg=s.total_density_avg,
                crossline_in_total=s.crossline_in_total or 0,
                crossline_out_total=s.crossline_out_total or 0,
                crossline_stats=crosslines_data,
                regions=regions_data,
            )
        )

    return ApiResponse.success(data=HistoryResponse(series=series))


@router.get("/export", response_model=ApiResponse[ExportResponse])
async def export_data(
    source_id: str = Query(..., description="数据源 ID"),
    from_time: str = Query(..., alias="from", description="开始时间 (ISO 8601)"),
    to_time: str = Query(..., alias="to", description="结束时间 (ISO 8601)"),
    format: str = Query(default="csv", description="导出格式: csv / xlsx"),
    db: Session = Depends(get_db),
):
    """导出统计数据"""
    # 验证数据源存在
    source_repo = VideoSourceRepository(db)
    source = source_repo.get_by_id(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="数据源不存在")

    # 查询统计数据
    stats_repo = StatsRepository(db)
    stats = stats_repo.get_by_time_range(
        source_id=source_id,
        interval_type="1m",  # 导出使用最细粒度
        time_from=from_time,
        time_to=to_time,
    )

    if not stats:
        raise HTTPException(status_code=404, detail="该时间段内无数据")

    # 创建导出目录
    export_dir = Path(settings.BASE_DIR) / "downloads"
    export_dir.mkdir(parents=True, exist_ok=True)

    # 生成文件名
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in (source.name or source_id))
    filename = f"export_{safe_name}_{timestamp}.{format}"
    file_path = export_dir / filename

    # 导出 CSV
    if format == "csv":
        with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["时间", "平均人数", "平均密度", "最大人数", "最小人数"])
            for s in stats:
                writer.writerow([
                    s.time_bucket,
                    s.total_count_avg,
                    s.total_density_avg,
                    s.total_count_max,
                    s.total_count_min,
                ])
    elif format == "xlsx":
        # 简化版本，需要安装 openpyxl
        try:
            from openpyxl import Workbook
            wb = Workbook()
            ws = wb.active
            ws.append(["时间", "平均人数", "平均密度", "最大人数", "最小人数"])
            for s in stats:
                ws.append([
                    s.time_bucket,
                    s.total_count_avg,
                    s.total_density_avg,
                    s.total_count_max,
                    s.total_count_min,
                ])
            wb.save(file_path)
        except ImportError:
            raise HTTPException(status_code=500, detail="xlsx 导出需要安装 openpyxl")
    else:
        raise HTTPException(status_code=400, detail=f"不支持的格式: {format}")

    # 记录导出任务
    task_repo = ExportTaskRepository(db)
    task = ExportTask(
        task_id=str(uuid.uuid4()),
        source_id=source_id,
        export_type=format,
        status="completed",
        file_path=str(file_path),
    )
    task_repo.create(task)

    logger.info(f"数据已导出: {file_path}")

    return ApiResponse.success(data=ExportResponse(url=f"/downloads/{filename}"))
