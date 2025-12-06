"""SQLAlchemy CollaborativeSession model for shared analysis sessions."""
import uuid
from datetime import datetime, timedelta

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class CollaborativeSession(Base):
    """Model for collaborative analysis sessions.
    
    Allows authenticated users to share their analysis via a link/QR code.
    Guests can join and ask questions about the analysis.
    """
    
    __tablename__ = "collaborative_sessions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Analysis data for LLM context
    analysis_data = Column(JSON, nullable=False)  # {top_artists, top_styles, top_genres, explanation}
    image_url = Column(String(512), nullable=False)  # URL to the analyzed image
    
    # Session metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    is_active = Column(Boolean, default=True, index=True)
    
    # Active viewers count (updated via heartbeat)
    active_viewers = Column(Integer, default=0)
    
    # Relationship
    owner = relationship("User", backref="collaborative_sessions")
    
    @classmethod
    def create_session(cls, owner_id: int, analysis_data: dict, image_url: str, duration_minutes: int = 40):
        """Factory method to create a new session with expiration."""
        return cls(
            owner_id=owner_id,
            analysis_data=analysis_data,
            image_url=image_url,
            expires_at=datetime.utcnow() + timedelta(minutes=duration_minutes)
        )
    
    @property
    def is_expired(self) -> bool:
        """Check if the session has expired."""
        return datetime.utcnow() > self.expires_at
    
    @property
    def remaining_seconds(self) -> int:
        """Get remaining time in seconds."""
        delta = self.expires_at - datetime.utcnow()
        return max(0, int(delta.total_seconds()))
    
    def __repr__(self):
        return f"<CollaborativeSession(id={self.id}, owner_id={self.owner_id}, active={self.is_active})>"
