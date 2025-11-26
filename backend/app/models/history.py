"""SQLAlchemy AnalysisHistory model."""
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base


class AnalysisHistory(Base):
    """Model for storing user's analysis history."""
    
    __tablename__ = "analysis_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Image info
    image_filename = Column(String(255), nullable=False)  # Unique filename on server
    image_url = Column(String(512), nullable=True)  # URL for frontend access
    
    # Top prediction (for quick display in history list)
    top_artist_slug = Column(String(100), nullable=False)
    top_artist_probability = Column(String(20), nullable=True)
    
    # Full analysis result as JSON
    analysis_result = Column(JSON, nullable=False)
    
    # Deep analysis result as JSON (optional, added later)
    deep_analysis_result = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationship
    user = relationship("User", back_populates="history")
    
    def __repr__(self):
        return f"<AnalysisHistory(id={self.id}, user_id={self.user_id}, artist={self.top_artist_slug})>"
