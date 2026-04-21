"""CrossLine Schema"""

from typing import Optional

from pydantic import BaseModel, Field


class CrossLineCreate(BaseModel):
    """创建计数线段"""
    source_id: str = Field(..., description="数据源 ID")
    name: str = Field(..., description="线段名称")
    start_x: float = Field(..., ge=0, le=100, description="起点 x%")
    start_y: float = Field(..., ge=0, le=100, description="起点 y%")
    end_x: float = Field(..., ge=0, le=100, description="终点 x%")
    end_y: float = Field(..., ge=0, le=100, description="终点 y%")
    direction: str = Field(default="in", description="计数方向")
    color: str = Field(default="#00FF00", description="显示颜色")


class CrossLineUpdate(BaseModel):
    """更新计数线段"""
    name: Optional[str] = None
    start_x: Optional[float] = Field(default=None, ge=0, le=100)
    start_y: Optional[float] = Field(default=None, ge=0, le=100)
    end_x: Optional[float] = Field(default=None, ge=0, le=100)
    end_y: Optional[float] = Field(default=None, ge=0, le=100)
    direction: Optional[str] = None
    color: Optional[str] = None


class CrossLineResponse(BaseModel):
    """计数线段响应"""
    line_id: str
    source_id: str
    name: str
    start_x: float
    start_y: float
    end_x: float
    end_y: float
    direction: str
    color: str


class CrossLineListResponse(BaseModel):
    """计数线段列表响应"""
    lines: list[CrossLineResponse]
