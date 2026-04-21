"""
Media Upload and Analysis Provisioning
======================================
This module provides the HTTP endpoints for uploading media files into the 
system and tracking the status of subsequent analysis jobs. 
"""

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
import uuid

# Project-wide utilities and patterns
from shared.database.base import get_db
from shared.models import Analysis, AnalysisStatus, User
from shared.utils import verify_token
from app.services.storage_service import storage_service
from app.services.file_validator import validate_upload_file, get_file_extension

# Declaration of the router for upload-related operations
router = APIRouter(prefix="/upload", tags=["Upload management"])


async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency that extracts the user identity from the JWT authorization token.
    
    Validates token presence, format, and authenticity before performing 
    a consistency check against the database.
    
    Args:
        authorization (str): Bearer token from the header.
        db (Session): Database session.
        
    Returns:
        User: The authenticated user profile.
        
    Raises:
        HTTPException: 401 if authentication fails at any stage.
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Session expired or authorization header missing",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Malformed authorization token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    token = authorization.replace("Bearer ", "")
    
    try:
        # Decode and verify the cryptographic signature of the token
        payload = verify_token(token)
        user_id = payload.get("user_id")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Identity claim missing in token")
        
        # Verify the user remains active in the system
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="User account is deactivated or missing")
        
        return user
        
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Identity verification failed")


@router.post("/")
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Main ingestion endpoint for deepfake analysis.
    
    Accepts media files, performs security and type validation, stores the 
    raw bytes in object storage, and initiates a tracking entry in the 
    analysis database.
    
    Args:
        file: The raw binary media (image/video).
        current_user: Authenticated identity injected by dependency.
        db: Scoped database session.
        
    Returns:
        dict: Metatada of the created analysis job, including the UUID ID.
    """
    # Defensive validation: check file size, magic numbers, and integrity
    content, mime_type, file_size = await validate_upload_file(file)
    
    # Generate a unique path in the bucket partitioned by user ID to prevent collisions
    file_extension = get_file_extension(mime_type)
    object_name = f"uploads/{current_user.id}/{uuid.uuid4()}{file_extension}"
    
    try:
        # Persist the file into MinIO object storage
        storage_service.upload_file(content, object_name, mime_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Media persistence failure: {str(e)}")
    
    # Register the analysis task in the audit database
    analysis = Analysis(
        user_id=current_user.id,
        file_name=file.filename,
        file_path=object_name,
        file_size=file_size,
        mime_type=mime_type,
        status=AnalysisStatus.PENDING,
        file_metadata={
            "original_filename": file.filename,
            "upload_timestamp": datetime.utcnow().isoformat(),
            "source_ip": "internal-gateway"
        }
    )
    
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    
    print(f"Media ingestion complete: {file.filename} persisted as {object_name} [ID: {analysis.id}]")
    
    return {
        "analysis_id": str(analysis.id),
        "status": analysis.status.value,
        "file_name": analysis.file_name,
        "file_size": analysis.file_size,
        "mime_type": analysis.mime_type,
        "message": "Media successfully uploaded and queued for processing"
    }


@router.get("/status/{analysis_id}")
async def get_upload_status(
    analysis_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Status monitoring endpoint for an individual analysis session.
    
    Provides real-time state information and any error telemetry surfaced 
    during detection. Only the owner of the media can query its status.
    
    Args:
        analysis_id (str): The UUID of the analysis record.
    """
    # Fetch record from the shared analysis table
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Requested analysis session not found")
    
    # Enforcement of ownership to prevent unauthorized data access
    if str(analysis.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Unauthorized access to analysis metrics")
    
    return {
        "analysis_id": str(analysis.id),
        "status": analysis.status.value,
        "progress": analysis.progress,
        "file_name": analysis.file_name,
        "created_at": analysis.created_at.isoformat(),
        "error_message": analysis.error_message
    }