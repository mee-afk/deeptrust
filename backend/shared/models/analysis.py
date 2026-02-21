"""Analysis model - tracks deepfake detection requests."""
from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, Text, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from shared.database.base import Base


class AnalysisStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    status = Column(Enum(AnalysisStatus), default=AnalysisStatus.PENDING, nullable=False, index=True)
    progress = Column(Integer, default=0, nullable=False)
    file_metadata = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="analyses")
    result = relationship("AnalysisResult", back_populates="analysis", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Analysis {self.id} - {self.status.value}>"

# """
# Analysis model - tracks deepfake detection requests.
# """
# from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, Text, Integer
# from sqlalchemy.dialects.postgresql import UUID, JSONB
# from sqlalchemy.orm import relationship
# from datetime import datetime
# import uuid
# import enum

# from backend.shared.database.base import Base


# class AnalysisStatus(str, enum.Enum):
#     """Analysis processing status"""
#     PENDING = "pending"
#     PROCESSING = "processing"
#     COMPLETED = "completed"
#     FAILED = "failed"
#     CANCELLED = "cancelled"


# class Analysis(Base):
#     """
#     Analysis request tracking.
#     Manages lifecycle from upload to completion.
#     """
#     __tablename__ = "analyses"

#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
#     user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)

#     # File information
#     file_name = Column(String(255), nullable=False)
#     file_path = Column(String(500), nullable=False)
#     file_size = Column(Integer, nullable=False)
#     mime_type = Column(String(100), nullable=False)

#     # Processing
#     status = Column(Enum(AnalysisStatus), default=AnalysisStatus.PENDING, nullable=False, index=True)
#     progress = Column(Integer, default=0, nullable=False)
#     metadata = Column(JSONB, nullable=True)
#     error_message = Column(Text, nullable=True)

#     # Timestamps
#     created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
#     started_at = Column(DateTime, nullable=True)
#     completed_at = Column(DateTime, nullable=True)

#     # Relationships
#     user = relationship("User", back_populates="analyses")
#     result = relationship("AnalysisResult", back_populates="analysis", uselist=False, cascade="all, delete-orphan")

#     def __repr__(self):
#         return f"<Analysis {self.id} - {self.status.value}>"

#     def to_dict(self):
#         """Convert to dictionary"""
#         return {
#             "id": str(self.id),
#             "user_id": str(self.user_id),
#             "file_name": self.file_name,
#             "file_size": self.file_size,
#             "mime_type": self.mime_type,
#             "status": self.status.value,
#             "progress": self.progress,
#             "created_at": self.created_at.isoformat()
#         }