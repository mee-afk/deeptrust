"""
File Integrity and Security Validation
======================================
This module provides a critical security layer for modern media handling. 
It validates incoming file streams against size constraints and uses libmagic 
to perform deep content inspection, ensuring that MIME types match actual 
binary signatures rather than relying on potentially spoofed extensions.
"""

from fastapi import UploadFile, HTTPException
import magic
import os
from typing import Tuple

# Environment configuration for maximum permissible payload size.
# Defaults to 100MB to allow for high-resolution video frames.
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 100 * 1024 * 1024))

# Explicit whitelisting of supported media types to prevent injection or invalid processing.
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/jpg", "image/webp"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/mpeg", "video/quicktime", "video/x-msvideo"}
ALLOWED_TYPES = ALLOWED_IMAGE_TYPES | ALLOWED_VIDEO_TYPES


async def validate_upload_file(file: UploadFile) -> Tuple[bytes, str, int]:
    """
    Performs comprehensive validation of an uploaded media file.
    
    Validates:
    - Non-zero length (empty file detection).
    - Payload size vs configurable threshold.
    - Actual binary content type via magic numbers (libmagic).
    
    Args:
        file (UploadFile): The raw upload handle from the FastAPI router.
        
    Returns:
        Tuple[bytes, str, int]: The validated binary content, detected MIME type, 
                               and total file size in bytes.
                               
    Raises:
        HTTPException: 400 status if any validation constraint is violated.
    """
    # Ingest file content into memory for inspection
    content = await file.read()
    file_size = len(content)
    
    # Check 1: Reject zero-byte uploads
    if file_size == 0:
        raise HTTPException(status_code=400, detail="The provided file appears to be empty.")
    
    # Check 2: Enforcement of maximum payload size
    if file_size > MAX_FILE_SIZE:
        max_mb = MAX_FILE_SIZE / (1024 * 1024)
        raise HTTPException(
            status_code=400,
            detail=f"Uploaded file exceeds the maximum permissible size of {max_mb:.2f}MB"
        )
    
    # Check 3: Content-based MIME type detection. 
    # magic.from_buffer inspects the binary headers (magic numbers) to identify 
    # the true file type, which is more secure than trusting the user-provided headers.
    mime_type = magic.from_buffer(content, mime=True)
    
    # Check 4: Domain-specific type whitelisting (Imagers/Videos only)
    if mime_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"FileType '{mime_type}' is not supported. Supported: Images and standard Video formats."
        )
    
    return content, mime_type, file_size


def get_file_extension(mime_type: str) -> str:
    """
    Maps a verified MIME type to a standard file extension.
    
    Args:
        mime_type (str): The verified MIME type from validate_upload_file.
        
    Returns:
        str: A normalized file extension (including the leading dot).
    """
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
    # Default to .bin for unrecognized (but technically allowed) types to prevent ambiguity
    return mime_to_ext.get(mime_type, ".bin")


def is_image(mime_type: str) -> bool:
    """ 
    Predicate to determine if the given MIME type belongs to the image domain. 
    """
    return mime_type in ALLOWED_IMAGE_TYPES


def is_video(mime_type: str) -> bool:
    """ 
    Predicate to determine if the given MIME type belongs to the video domain. 
    """
    return mime_type in ALLOWED_VIDEO_TYPES