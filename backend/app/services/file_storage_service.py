"""File Storage Service

Handles video file upload, storage, and lifecycle management.

Design:
- Files stored in configurable directory (default: /data/uploads)
- File metadata stored in JSON sidecar files
- Automatic cleanup of expired files (configurable retention)
- Size and extension validation
"""

import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import aiofiles
from fastapi import UploadFile

from app.core.config import settings
from app.schemas.file import FileInfo, FileUploadResponse

logger = logging.getLogger(__name__)


class FileStorageError(Exception):
    """Base file storage error."""
    pass


class FileTooLargeError(FileStorageError):
    """File exceeds size limit."""
    pass


class InvalidFileTypeError(FileStorageError):
    """File type not allowed."""
    pass


class FileNotFoundError(FileStorageError):
    """File not found."""
    pass


class FileStorageService:
    """File storage service for video uploads.
    
    Features:
    - Streaming upload for large files
    - Extension and size validation
    - Metadata tracking via JSON sidecar
    - Automatic expiration
    """
    
    def __init__(
        self,
        storage_path: str = settings.file_storage_path,
        max_size_mb: int = settings.file_max_size_mb,
        retention_days: int = settings.file_retention_days,
        allowed_extensions: list[str] = None
    ):
        self.storage_path = Path(storage_path)
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.retention_days = retention_days
        self.allowed_extensions = allowed_extensions or settings.file_allowed_extensions
        
        # Ensure storage directory exists (skip if path is not writable)
        try:
            self.storage_path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.warning(f"Could not create storage directory {self.storage_path}: {e}")
        
        logger.info(
            f"FileStorageService initialized: path={self.storage_path}, "
            f"max_size={max_size_mb}MB, retention={retention_days}days"
        )
    
    def _get_extension(self, filename: str) -> str:
        """Extract file extension (lowercase, without dot)."""
        if "." in filename:
            return filename.rsplit(".", 1)[1].lower()
        return ""
    
    def _validate_extension(self, filename: str) -> None:
        """Validate file extension.
        
        Raises:
            InvalidFileTypeError: If extension not allowed
        """
        ext = self._get_extension(filename)
        if ext not in self.allowed_extensions:
            raise InvalidFileTypeError(
                f"File type '{ext}' not allowed. "
                f"Allowed types: {', '.join(self.allowed_extensions)}"
            )
    
    def _get_file_path(self, file_id: str) -> Path:
        """Get file path for given file_id."""
        return self.storage_path / file_id
    
    def _get_metadata_path(self, file_id: str) -> Path:
        """Get metadata file path for given file_id."""
        return self.storage_path / f"{file_id}.json"
    
    async def _save_metadata(self, file_info: FileInfo) -> None:
        """Save file metadata to JSON sidecar."""
        metadata_path = self._get_metadata_path(file_info.file_id)
        metadata = {
            "file_id": file_info.file_id,
            "filename": file_info.filename,
            "size": file_info.size,
            "content_type": file_info.content_type,
            "path": file_info.path,
            "created_at": file_info.created_at.isoformat(),
            "expires_at": file_info.expires_at.isoformat() if file_info.expires_at else None
        }
        async with aiofiles.open(metadata_path, "w") as f:
            await f.write(json.dumps(metadata, indent=2))
    
    async def _load_metadata(self, file_id: str) -> Optional[FileInfo]:
        """Load file metadata from JSON sidecar."""
        metadata_path = self._get_metadata_path(file_id)
        if not metadata_path.exists():
            return None
        
        try:
            async with aiofiles.open(metadata_path, "r") as f:
                content = await f.read()
                data = json.loads(content)
                return FileInfo(
                    file_id=data["file_id"],
                    filename=data["filename"],
                    size=data["size"],
                    content_type=data["content_type"],
                    path=data["path"],
                    created_at=datetime.fromisoformat(data["created_at"]),
                    expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None
                )
        except Exception as e:
            logger.error(f"Failed to load metadata for {file_id}: {e}")
            return None


    async def upload(self, file: UploadFile) -> FileUploadResponse:
        """Upload a video file.
        
        Args:
            file: FastAPI UploadFile object
            
        Returns:
            FileUploadResponse with file_id and metadata
            
        Raises:
            InvalidFileTypeError: If file type not allowed
            FileTooLargeError: If file exceeds size limit
        """
        # Validate extension
        filename = file.filename or "unknown"
        self._validate_extension(filename)
        
        # Generate unique file_id with extension
        ext = self._get_extension(filename)
        file_id = f"{uuid.uuid4()}.{ext}"
        file_path = self._get_file_path(file_id)
        
        logger.info(f"Starting file upload: filename={filename}, file_id={file_id}")
        
        # Stream file to disk with size check
        total_size = 0
        chunk_size = 1024 * 1024  # 1MB chunks
        
        try:
            async with aiofiles.open(file_path, "wb") as f:
                while True:
                    chunk = await file.read(chunk_size)
                    if not chunk:
                        break
                    
                    total_size += len(chunk)
                    
                    # Check size limit
                    if total_size > self.max_size_bytes:
                        # Clean up partial file
                        await f.close()
                        file_path.unlink(missing_ok=True)
                        raise FileTooLargeError(
                            f"File exceeds maximum size of {settings.file_max_size_mb}MB"
                        )
                    
                    await f.write(chunk)
            
            # Calculate expiration
            created_at = datetime.utcnow()
            expires_at = created_at + timedelta(days=self.retention_days)
            
            # Create file info
            file_info = FileInfo(
                file_id=file_id,
                filename=filename,
                size=total_size,
                content_type=file.content_type or "application/octet-stream",
                path=str(file_path),
                created_at=created_at,
                expires_at=expires_at
            )
            
            # Save metadata
            await self._save_metadata(file_info)
            
            logger.info(f"File uploaded: file_id={file_id}, size={total_size} bytes")
            
            return FileUploadResponse(
                file_id=file_id,
                filename=filename,
                size=total_size,
                content_type=file_info.content_type,
                created_at=created_at
            )
            
        except (FileTooLargeError, InvalidFileTypeError):
            raise
        except Exception as e:
            # Clean up on error
            file_path.unlink(missing_ok=True)
            logger.error(f"File upload failed: {e}")
            raise FileStorageError(f"Failed to upload file: {e}") from e
    
    async def get(self, file_id: str) -> FileInfo:
        """Get file info.
        
        Args:
            file_id: Unique file identifier
            
        Returns:
            FileInfo object
            
        Raises:
            FileNotFoundError: If file not found
        """
        file_info = await self._load_metadata(file_id)
        if file_info is None:
            raise FileNotFoundError(f"File {file_id} not found")
        
        # Check if file still exists
        file_path = self._get_file_path(file_id)
        if not file_path.exists():
            raise FileNotFoundError(f"File {file_id} not found on disk")
        
        return file_info
    
    async def delete(self, file_id: str) -> bool:
        """Delete a file.
        
        Args:
            file_id: Unique file identifier
            
        Returns:
            bool: Whether deletion succeeded
        """
        file_path = self._get_file_path(file_id)
        metadata_path = self._get_metadata_path(file_id)
        
        deleted = False
        
        if file_path.exists():
            file_path.unlink()
            deleted = True
            logger.info(f"File deleted: file_id={file_id}")
        
        if metadata_path.exists():
            metadata_path.unlink()
        
        return deleted
    
    async def list_files(self) -> list[FileInfo]:
        """List all files.
        
        Returns:
            List of FileInfo objects
        """
        files = []
        
        for metadata_file in self.storage_path.glob("*.json"):
            file_id = metadata_file.stem
            file_info = await self._load_metadata(file_id)
            if file_info:
                files.append(file_info)
        
        return sorted(files, key=lambda f: f.created_at, reverse=True)
    
    async def cleanup_expired(self) -> int:
        """Clean up expired files.
        
        Returns:
            int: Number of files deleted
        """
        now = datetime.utcnow()
        deleted_count = 0
        
        for metadata_file in self.storage_path.glob("*.json"):
            file_id = metadata_file.stem
            file_info = await self._load_metadata(file_id)
            
            if file_info and file_info.expires_at and file_info.expires_at < now:
                if await self.delete(file_id):
                    deleted_count += 1
                    logger.info(f"Expired file cleaned up: file_id={file_id}")
        
        if deleted_count > 0:
            logger.info(f"Cleanup completed: {deleted_count} expired files deleted")
        
        return deleted_count
    
    def get_container_path(self, file_id: str) -> str:
        """Get file path as seen from ZLMediaKit container.
        
        In docker-compose, uploads directory is mounted to /data/uploads.
        
        Args:
            file_id: Unique file identifier
            
        Returns:
            str: Container-accessible file path
        """
        # The container path is /data/uploads/{file_id}
        return f"/data/uploads/{file_id}"


# Global file storage service instance
_file_storage_service: Optional[FileStorageService] = None


def get_file_storage_service() -> FileStorageService:
    """Get file storage service (singleton)."""
    global _file_storage_service
    if _file_storage_service is None:
        _file_storage_service = FileStorageService()
    return _file_storage_service


def reset_file_storage_service() -> None:
    """Reset file storage service (for testing)."""
    global _file_storage_service
    _file_storage_service = None
