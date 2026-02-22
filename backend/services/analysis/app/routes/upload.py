"""
File upload endpoints.
Handles media uploads and creates analysis records.
"""
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
import uuid

from shared.database.base import get_db
from shared.models import Analysis, AnalysisStatus, User
from shared.utils import verify_token
from app.services.storage_service import storage_service
from app.services.file_validator import validate_upload_file, get_file_extension

router = APIRouter(prefix="/upload", tags=["Upload"])


async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """Extract and validate user from Authorization header."""
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization format",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    token = authorization.replace("Bearer ", "")
    
    try:
        payload = verify_token(token)
        user_id = payload.get("user_id")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="User not found")
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail="Token validation failed")


@router.post("/")
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload media file for deepfake analysis."""
    content, mime_type, file_size = await validate_upload_file(file)
    
    file_extension = get_file_extension(mime_type)
    object_name = f"uploads/{current_user.id}/{uuid.uuid4()}{file_extension}"
    
    try:
        storage_service.upload_file(content, object_name, mime_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Storage failed: {str(e)}")
    
    analysis = Analysis(
        user_id=current_user.id,
        file_name=file.filename,
        file_path=object_name,
        file_size=file_size,
        mime_type=mime_type,
        status=AnalysisStatus.PENDING,
        file_metadata={
            "original_filename": file.filename,
            "upload_timestamp": datetime.utcnow().isoformat()
        }
    )
    
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    
    print(f"✅ Uploaded: {file.filename} -> {object_name} (ID: {analysis.id})")
    
    return {
        "analysis_id": str(analysis.id),
        "status": analysis.status.value,
        "file_name": analysis.file_name,
        "file_size": analysis.file_size,
        "mime_type": analysis.mime_type,
        "message": "File uploaded successfully"
    }


@router.get("/status/{analysis_id}")
async def get_upload_status(
    analysis_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get upload/analysis status by ID"""
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    if str(analysis.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return {
        "analysis_id": str(analysis.id),
        "status": analysis.status.value,
        "progress": analysis.progress,
        "file_name": analysis.file_name,
        "created_at": analysis.created_at.isoformat(),
        "error_message": analysis.error_message
    }