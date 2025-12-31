"""File Upload REST API

Provides video file upload and management endpoints.
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.logging import get_logger, log_error, log_info

logger = get_logger(__name__)
from app.schemas.file import FileInfoPublic, FileListResponse, FileUploadResponse
from app.services.file_storage_service import (
    FileNotFoundError,
    FileStorageError,
    FileStorageService,
    FileTooLargeError,
    InvalidFileTypeError,
    get_file_storage_service,
)

router = APIRouter()


@router.post(
    "/upload",
    response_model=FileUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload video file",
    description=f"""
Upload a video file for streaming.

**Supported formats**: {', '.join(settings.file_allowed_extensions)}

**Size limit**: {settings.file_max_size_mb}MB

**Retention**: Files are automatically deleted after {settings.file_retention_days} days.

The returned `file_id` can be used when creating a video stream with type='file'.
"""
)
async def upload_file(
    file: UploadFile = File(..., description="Video file to upload"),
    storage: FileStorageService = Depends(get_file_storage_service),
) -> FileUploadResponse:
    """Upload a video file.
    
    The file will be stored and can be used to create a video stream.
    Use the returned file_id when calling POST /api/streams with type='file'.
    """
    log_info(logger, "Uploading file", filename=file.filename)
    try:
        result = await storage.upload(file)
        log_info(logger, "File uploaded", file_id=result.file_id, filename=file.filename)
        return result
    except InvalidFileTypeError as e:
        log_error(logger, "Invalid file type", filename=file.filename, error=e)
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(e)
        )
    except FileTooLargeError as e:
        log_error(logger, "File too large", filename=file.filename, error=e)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(e)
        )
    except FileStorageError as e:
        log_error(logger, "File storage error", filename=file.filename, error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "",
    response_model=FileListResponse,
    summary="List uploaded files",
    description="Get a list of all uploaded video files."
)
async def list_files(
    storage: FileStorageService = Depends(get_file_storage_service),
) -> FileListResponse:
    """List all uploaded files."""
    files = await storage.list_files()
    # Convert to public schema (without internal path)
    public_files = [f.to_public() for f in files]
    return FileListResponse(files=public_files, total=len(public_files))


@router.get(
    "/{file_id}",
    response_model=FileInfoPublic,
    summary="Get file info",
    description="Get information about an uploaded file."
)
async def get_file(
    file_id: str,
    storage: FileStorageService = Depends(get_file_storage_service),
) -> FileInfoPublic:
    """Get file information."""
    try:
        file_info = await storage.get(file_id)
        return file_info.to_public()
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File {file_id} not found"
        )


@router.delete(
    "/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete file",
    description="Delete an uploaded file. Associated streams will enter ERROR state."
)
async def delete_file(
    file_id: str,
    storage: FileStorageService = Depends(get_file_storage_service),
) -> None:
    """Delete an uploaded file.
    
    Note: If a stream is using this file, it will enter ERROR state.
    """
    log_info(logger, "Deleting file", file_id=file_id)
    try:
        await storage.get(file_id)  # Check if exists
        await storage.delete(file_id)
        log_info(logger, "File deleted", file_id=file_id)
    except FileNotFoundError:
        log_error(logger, "File not found for delete", file_id=file_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File {file_id} not found"
        )


@router.post(
    "/cleanup",
    summary="Cleanup expired files",
    description="Manually trigger cleanup of expired files."
)
async def cleanup_files(
    storage: FileStorageService = Depends(get_file_storage_service),
) -> dict:
    """Cleanup expired files.
    
    This is normally done automatically, but can be triggered manually.
    """
    log_info(logger, "Starting file cleanup")
    deleted_count = await storage.cleanup_expired()
    log_info(logger, "File cleanup completed", deleted_count=deleted_count)
    return {"deleted_count": deleted_count}
