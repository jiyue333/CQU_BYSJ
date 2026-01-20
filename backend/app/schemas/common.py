"""
通用 Schema

统一响应格式和分页参数
"""

from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """统一 API 响应格式"""

    code: int = Field(default=0, description="状态码，0 成功，非 0 失败")
    data: Optional[T] = Field(default=None, description="业务数据")
    msg: str = Field(default="success", description="提示信息")

    @classmethod
    def success(cls, data: T = None, msg: str = "success") -> "ApiResponse[T]":
        """成功响应"""
        return cls(code=0, data=data, msg=msg)

    @classmethod
    def error(cls, code: int = 1, msg: str = "error") -> "ApiResponse":
        """错误响应"""
        return cls(code=code, data=None, msg=msg)


class PaginationParams(BaseModel):
    """分页参数"""

    skip: int = Field(default=0, ge=0, description="跳过记录数")
    limit: int = Field(default=100, ge=1, le=1000, description="返回记录数")


class OkResponse(BaseModel):
    """简单成功响应"""

    ok: bool = True
