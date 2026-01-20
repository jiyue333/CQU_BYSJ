"""
导出 Schema

Export 相关的请求/响应模型
"""

from pydantic import BaseModel, Field


class ExportRequest(BaseModel):
    """导出请求参数"""

    source_id: str = Field(..., description="数据源 ID")
    from_time: str = Field(..., alias="from", description="开始时间 (ISO 8601)")
    to_time: str = Field(..., alias="to", description="结束时间 (ISO 8601)")
    format: str = Field(default="csv", description="导出格式: csv / xlsx")

    model_config = {"populate_by_name": True}


class ExportResponse(BaseModel):
    """导出响应"""

    url: str = Field(..., description="下载链接")


class ExportTaskResponse(BaseModel):
    """导出任务响应"""

    task_id: str = Field(..., description="任务 ID")
    source_id: str = Field(..., description="数据源 ID")
    status: str = Field(..., description="状态: pending/processing/completed/failed")
    file_path: str | None = Field(default=None, description="文件路径")
    created_at: str = Field(..., description="创建时间")

    model_config = {"from_attributes": True}
