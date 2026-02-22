"""
File validation for uploads.
Validates file type, size, and content.
"""
from fastapi import UploadFile, HTTPException
import magic
import os
from typing import Tuple

# Configuration
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 100 * 1024 * 1024))  # 100MB default
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/jpg", "image/webp"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/mpeg", "video/quicktime", "video/x-msvideo"}
ALLOWED_TYPES = ALLOWED_IMAGE_TYPES | ALLOWED_VIDEO_TYPES


async def validate_upload_file(file: UploadFile) -> Tuple[bytes, str, int]:
    """
    Validate uploaded file.
    
    Args:
        file: FastAPI UploadFile object
        
    Returns:
        Tuple of (file_content, mime_type, file_size)
        
    Raises:
        HTTPException: If validation fails
    """
    # Read file content
    content = await file.read()
    file_size = len(content)
    
    # Check file size
    if file_size == 0:
        raise HTTPException(status_code=400, detail="Empty file")
    
    if file_size > MAX_FILE_SIZE:
        max_mb = MAX_FILE_SIZE / (1024 * 1024)
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {max_mb}MB"
        )
    
    # Detect MIME type from content (not extension)
    mime_type = magic.from_buffer(content, mime=True)
    
    # Validate MIME type
    if mime_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {mime_type}. Allowed: images and videos only"
        )
    
    return content, mime_type, file_size


def get_file_extension(mime_type: str) -> str:
    """Get file extension from MIME type"""
    mime_to_ext = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "video/mp4": ".mp4",
        "video/mpeg": ".mpeg",
        "video/quicktime": ".mov",
        "video/x-msvideo": ".avi"
    }
    return mime_to_ext.get(mime_type, ".bin")


def is_image(mime_type: str) -> bool:
    """Check if MIME type is an image"""
    return mime_type in ALLOWED_IMAGE_TYPES


def is_video(mime_type: str) -> bool:
    """Check if MIME type is a video"""
    return mime_type in ALLOWED_VIDEO_TYPES