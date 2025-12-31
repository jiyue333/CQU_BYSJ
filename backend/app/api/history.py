"""历史数据查询 REST API

提供历史数据查询和导出接口。

Requirements: 6.2, 6.4
"""

import csv
import io
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import get_logger, log_error, log_info

logger = get_logger(__name__)
from app.schemas.history_stat import (
    AggregatedHistoryResponse,
    AggregationGranularity,
    HistoryListResponse,
)
from app.services.history_storage_service import get_history_storage_service
from app.services.stream_service import StreamNotFoundError, get_stream_service

router = APIRouter()


@router.get(
    "/{stream_id}/history",
    response_model=HistoryListResponse,
    summary="查询历史数据",
    description="查询指定视频流的历史统计数据，支持时间范围过滤和分页。"
)
async def get_history(
    stream_id: str,
    start_time: Optional[datetime] = Query(None, description="开始时间 (ISO 8601)"),
    end_time: Optional[datetime] = Query(None, description="结束时间 (ISO 8601)"),
    limit: int = Query(100, ge=1, le=1000, description="返回记录数限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    db: AsyncSession = Depends(get_db),
) -> HistoryListResponse:
    """查询历史数据
    
    返回指定视频流的历史统计数据，按时间倒序排列。
    """
    # 验证流是否存在
    stream_service = get_stream_service(db)
    try:
        await stream_service.get_or_raise(stream_id)
    except StreamNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stream {stream_id} not found"
        )
    
    # 验证时间范围
    if start_time and end_time and end_time < start_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_time must be greater than or equal to start_time"
        )
    
    # 查询历史数据
    history_service = get_history_storage_service()
    return await history_service.query_history(
        session=db,
        stream_id=stream_id,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{stream_id}/history/aggregated",
    response_model=AggregatedHistoryResponse,
    summary="查询聚合历史数据",
    description="查询指定视频流的聚合历史数据，支持按分钟/小时/天聚合。"
)
async def get_aggregated_history(
    stream_id: str,
    granularity: AggregationGranularity = Query(
        AggregationGranularity.MINUTE,
        description="聚合粒度"
    ),
    start_time: Optional[datetime] = Query(None, description="开始时间 (ISO 8601)"),
    end_time: Optional[datetime] = Query(None, description="结束时间 (ISO 8601)"),
    db: AsyncSession = Depends(get_db),
) -> AggregatedHistoryResponse:
    """查询聚合历史数据
    
    返回按指定粒度聚合的历史数据，包含平均值、最大值、最小值等统计信息。
    """
    # 验证流是否存在
    stream_service = get_stream_service(db)
    try:
        await stream_service.get_or_raise(stream_id)
    except StreamNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stream {stream_id} not found"
        )
    
    # 验证时间范围
    if start_time and end_time and end_time < start_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_time must be greater than or equal to start_time"
        )
    
    # 查询聚合数据
    history_service = get_history_storage_service()
    return await history_service.query_aggregated_history(
        session=db,
        stream_id=stream_id,
        granularity=granularity,
        start_time=start_time,
        end_time=end_time,
    )


@router.get(
    "/{stream_id}/history/export",
    summary="导出历史数据",
    description="导出指定视频流的历史数据为 CSV 格式。"
)
async def export_history(
    stream_id: str,
    start_time: Optional[datetime] = Query(None, description="开始时间 (ISO 8601)"),
    end_time: Optional[datetime] = Query(None, description="结束时间 (ISO 8601)"),
    format: str = Query("csv", description="导出格式 (csv/excel)"),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """导出历史数据
    
    支持 CSV 和 Excel 格式导出。
    """
    log_info(logger, "Exporting history", stream_id=stream_id, format=format)
    
    # 验证流是否存在
    stream_service = get_stream_service(db)
    try:
        await stream_service.get_or_raise(stream_id)
    except StreamNotFoundError:
        log_error(logger, "Stream not found for export", stream_id=stream_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stream {stream_id} not found"
        )
    
    # 验证格式
    if format not in ("csv", "excel"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="format must be 'csv' or 'excel'"
        )
    
    # 查询所有数据（不分页）
    history_service = get_history_storage_service()
    result = await history_service.query_history(
        session=db,
        stream_id=stream_id,
        start_time=start_time,
        end_time=end_time,
        limit=10000,  # 最大导出 10000 条
        offset=0,
    )
    
    log_info(logger, "History export completed", stream_id=stream_id, record_count=result.total)
    
    if format == "csv":
        return _export_csv(stream_id, result)
    else:
        return _export_excel(stream_id, result)


def _export_csv(stream_id: str, result: HistoryListResponse) -> StreamingResponse:
    """导出为 CSV 格式"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # 写入表头
    writer.writerow([
        "timestamp",
        "total_count",
        "region_id",
        "region_name",
        "region_count",
        "region_density",
        "region_level",
    ])
    
    # 写入数据
    for stat in result.stats:
        if stat.region_stats:
            for region in stat.region_stats:
                writer.writerow([
                    stat.timestamp.isoformat(),
                    stat.total_count,
                    region.region_id,
                    region.region_name,
                    region.count,
                    region.density,
                    region.level.value,
                ])
        else:
            writer.writerow([
                stat.timestamp.isoformat(),
                stat.total_count,
                "",
                "",
                "",
                "",
                "",
            ])
    
    output.seek(0)
    
    filename = f"history_{stream_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


def _export_excel(stream_id: str, result: HistoryListResponse) -> StreamingResponse:
    """导出为 Excel 格式"""
    try:
        import openpyxl
        from openpyxl import Workbook
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Excel export requires openpyxl package"
        )
    
    wb = Workbook()
    ws = wb.active
    ws.title = "History Data"
    
    # 写入表头
    headers = [
        "timestamp",
        "total_count",
        "region_id",
        "region_name",
        "region_count",
        "region_density",
        "region_level",
    ]
    ws.append(headers)
    
    # 写入数据
    for stat in result.stats:
        if stat.region_stats:
            for region in stat.region_stats:
                ws.append([
                    stat.timestamp.isoformat(),
                    stat.total_count,
                    region.region_id,
                    region.region_name,
                    region.count,
                    region.density,
                    region.level.value,
                ])
        else:
            ws.append([
                stat.timestamp.isoformat(),
                stat.total_count,
                "",
                "",
                "",
                "",
                "",
            ])
    
    # 保存到内存
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    filename = f"history_{stream_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )
