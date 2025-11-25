"""Pydantic schemas for request/response validation."""
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field


# ============ Auth Schemas ============

class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)


class UserCreate(UserBase):
    """Schema for user registration."""
    password: str = Field(..., min_length=6, max_length=100)


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class UserResponse(UserBase):
    """Schema for user response."""
    id: int
    is_active: bool
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token payload data."""
    user_id: Optional[int] = None
    email: Optional[str] = None


# ============ Analysis Schemas ============

class ArtistPrediction(BaseModel):
    """Single artist prediction."""
    index: int
    artist_slug: str
    probability: float = Field(..., ge=0.0, le=1.0)
    
    @property
    def artist_name(self) -> str:
        """Convert slug to readable name."""
        return self.artist_slug.replace("-", " ").title()


class GenrePrediction(BaseModel):
    """Single genre prediction."""
    index: int
    name: str
    probability: float = Field(..., ge=0.0, le=1.0)
    
    @property
    def display_name(self) -> str:
        """Convert to readable name."""
        return self.name.replace("_", " ").title()


class StylePrediction(BaseModel):
    """Single style prediction."""
    index: int
    name: str
    probability: float = Field(..., ge=0.0, le=1.0)
    
    @property
    def display_name(self) -> str:
        """Convert to readable name."""
        return self.name.replace("_", " ").title()


class AnalysisExplanation(BaseModel):
    """LLM-generated explanation (stub for now)."""
    text: str
    source: str = "stub"  # "stub" or "llm"


class GeneratedThumbnail(BaseModel):
    """Generated image thumbnail (ComfyUI stub for now)."""
    url: str
    artist_slug: str
    prompt: Optional[str] = None


class AnalysisRequest(BaseModel):
    """Request body for analysis (if needed for JSON body in future)."""
    pass


class AnalysisResponse(BaseModel):
    """Full analysis response."""
    success: bool = True
    image_path: str
    top_artists: List[ArtistPrediction]
    top_genres: List[GenrePrediction] = []
    top_styles: List[StylePrediction] = []
    explanation: AnalysisExplanation
    generated_thumbnails: List[GeneratedThumbnail]
    message: Optional[str] = None


class ErrorResponse(BaseModel):
    """Error response schema."""
    success: bool = False
    error: str
    detail: Optional[str] = None
