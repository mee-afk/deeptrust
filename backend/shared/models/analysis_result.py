"""Analysis result model - stores detection outcomes."""
from sqlalchemy import Column, Float, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from shared.database.base import Base


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    analysis_id = Column(UUID(as_uuid=True), ForeignKey('analyses.id', ondelete='CASCADE'), primary_key=True)
    is_deepfake = Column(Boolean, nullable=False)
    confidence_score = Column(Float, nullable=False)
    mesonet_score = Column(Float, nullable=True)
    xception_score = Column(Float, nullable=True)
    frequency_score = Column(Float, nullable=True)
    biological_score = Column(Float, nullable=True)
    ensemble_weights = Column(JSONB, nullable=False)
    voting_breakdown = Column(JSONB, nullable=True)
    gradcam_paths = Column(JSONB, nullable=True)
    frequency_analysis = Column(JSONB, nullable=True)
    biological_analysis = Column(JSONB, nullable=True)
    artifacts_detected = Column(JSONB, nullable=True)
    processing_time = Column(Float, nullable=True)
    model_versions = Column(JSONB, nullable=True)

    analysis = relationship("Analysis", back_populates="result")

    def __repr__(self):
        verdict = "DEEPFAKE" if self.is_deepfake else "AUTHENTIC"
        return f"<AnalysisResult {self.analysis_id} - {verdict}>"

# """
# Analysis result model - stores detection outcomes and explainability data.
# """
# from sqlalchemy import Column, Float, ForeignKey, Boolean
# from sqlalchemy.dialects.postgresql import UUID, JSONB
# from sqlalchemy.orm import relationship

# from backend.shared.database.base import Base


# class AnalysisResult(Base):
#     """
#     Deepfake detection results with explainability.
#     """
#     __tablename__ = "analysis_results"

#     analysis_id = Column(UUID(as_uuid=True), ForeignKey('analyses.id', ondelete='CASCADE'), primary_key=True)

#     # Predictions
#     is_deepfake = Column(Boolean, nullable=False)
#     confidence_score = Column(Float, nullable=False)

#     # Model scores
#     mesonet_score = Column(Float, nullable=True)
#     xception_score = Column(Float, nullable=True)
#     frequency_score = Column(Float, nullable=True)
#     biological_score = Column(Float, nullable=True)

#     # Ensemble data
#     ensemble_weights = Column(JSONB, nullable=False)
#     voting_breakdown = Column(JSONB, nullable=True)

#     # Explainability
#     gradcam_paths = Column(JSONB, nullable=True)
#     frequency_analysis = Column(JSONB, nullable=True)
#     biological_analysis = Column(JSONB, nullable=True)
#     artifacts_detected = Column(JSONB, nullable=True)

#     # Metadata
#     processing_time = Column(Float, nullable=True)
#     model_versions = Column(JSONB, nullable=True)

#     # Relationships
#     analysis = relationship("Analysis", back_populates="result")

#     def __repr__(self):
#         verdict = "DEEPFAKE" if self.is_deepfake else "AUTHENTIC"
#         return f"<AnalysisResult {self.analysis_id} - {verdict}>"

#     def to_dict(self):
#         """Convert to dictionary"""
#         return {
#             "analysis_id": str(self.analysis_id),
#             "is_deepfake": self.is_deepfake,
#             "confidence_score": self.confidence_score,
#             "mesonet_score": self.mesonet_score,
#             "xception_score": self.xception_score,
#             "frequency_score": self.frequency_score,
#             "biological_score": self.biological_score
#         }