"""File upload schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class FileUploadResponse(BaseModel):
    """File upload response."""
    file_id: str = Field(..., description="Unique file identifier")
    filename: str = Field(..., description="Original filename")
    size: int = Field(..., description="File size in bytes")
    content_type: str = Field(..., description="MIME content type")
    created_at: datetime = Field(..., description="Upload timestamp")


class FileInfoPublic(BaseModel):
    """Public file information (without internal path)."""
    file_id: str = Field(..., description="Unique file identifier")
    filename: str = Field(..., description="Original filename")
    size: int = Field(..., description="File size in bytes")
    content_type: str = Field(..., description="MIME content type")
    created_at: datetime = Field(..., description="Upload timestamp")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")


class FileInfo(BaseModel):
    """Internal file information (includes storage path)."""
    file_id: str = Field(..., description="Unique file identifier")
    filename: str = Field(..., description="Original filename")
    size: int = Field(..., description="File size in bytes")
    content_type: str = Field(..., description="MIME content type")
    path: str = Field(..., description="Storage path (internal use only)")
    created_at: datetime = Field(..., description="Upload timestamp")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")
    
    def to_public(self) -> FileInfoPublic:
        """Convert to public schema (without internal path)."""
        return FileInfoPublic(
            file_id=self.file_id,
            filename=self.filename,
            size=self.size,
            content_type=self.content_type,
            created_at=self.created_at,
            expires_at=self.expires_at
        )


class FileListResponse(BaseModel):
    """File list response."""
    files: list[FileInfoPublic] = Field(default_factory=list)
    total: int = Field(0, description="Total file count")
