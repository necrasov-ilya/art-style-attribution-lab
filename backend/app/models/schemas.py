"""Pydantic schemas for request/response validation."""
from datetime import datetime
from typing import List, Optional, Any, Dict
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
    message: Optional[str] = None


# ============ Generation Schemas ============

class GenerateRequest(BaseModel):
    """Request for image generation."""
    artist_slug: str
    style_name: Optional[str] = None
    genre_name: Optional[str] = None
    user_prompt: Optional[str] = None  # Additional details from user
    count: int = Field(default=4, ge=1, le=8)


class GenerateResponse(BaseModel):
    """Response with generated images."""
    success: bool = True
    prompt: str  # The SD prompt that was used
    images: List[GeneratedThumbnail]
    message: Optional[str] = None


class ErrorResponse(BaseModel):
    """Error response schema."""
    success: bool = False
    error: str
    detail: Optional[str] = None


# ============ History Schemas ============

class HistoryItemBase(BaseModel):
    """Base history item schema."""
    top_artist_slug: str
    image_url: str
    analysis_result: Dict[str, Any]


class HistoryItemCreate(HistoryItemBase):
    """Schema for creating history item."""
    image_filename: str


class HistoryItemResponse(BaseModel):
    """Schema for history item in list."""
    id: int
    image_url: str
    top_artist_slug: str
    created_at: datetime
    analysis_result: Dict[str, Any]
    
    class Config:
        from_attributes = True


class HistoryListResponse(BaseModel):
    """Response with list of history items."""
    success: bool = True
    items: List[HistoryItemResponse]
    total: int


# ============ Deep Analysis Schemas ============

class DominantColor(BaseModel):
    """Single dominant color with metadata."""
    hex: str
    rgb: List[int] = Field(..., min_length=3, max_length=3)
    lab: List[float] = Field(..., min_length=3, max_length=3)
    percentage: float = Field(..., ge=0.0, le=1.0)
    name: Optional[str] = None  # Human-readable color name
    temperature: str = "neutral"  # "warm", "cool", "neutral"


class ColorFeatures(BaseModel):
    """Extracted color features from image."""
    dominant_colors: List[DominantColor]
    warm_ratio: float = Field(..., ge=0.0, le=1.0)
    cool_ratio: float = Field(..., ge=0.0, le=1.0)
    overall_contrast: float = Field(..., ge=0.0, le=1.0)
    overall_saturation: float = Field(..., ge=0.0, le=1.0)
    brightness: float = Field(..., ge=0.0, le=1.0)


class ColorPsychologyAnalysis(BaseModel):
    """LLM-generated color psychology analysis."""
    palette_interpretation: str  # Emotional interpretation of the palette
    mood_tags: List[str]  # e.g., ["melancholic", "warm", "energetic"]
    color_harmony: str  # Type of color harmony detected
    emotional_impact: str  # Description of emotional impact
    source: str = "llm"  # "llm" or "stub"


class CompositionFeatures(BaseModel):
    """Extracted composition features from image."""
    saliency_center_x: float  # Normalized 0-1
    saliency_center_y: float  # Normalized 0-1
    rule_of_thirds_alignment: float = Field(..., ge=0.0, le=1.0)  # How well key points align
    horizontal_symmetry: float = Field(..., ge=0.0, le=1.0)
    vertical_symmetry: float = Field(..., ge=0.0, le=1.0)
    visual_weight_distribution: str  # "balanced", "left-heavy", "right-heavy", "top-heavy", "bottom-heavy"
    focal_points: List[Dict[str, float]]  # [{x, y, strength}, ...]
    perspective_lines_detected: bool = False
    vanishing_points: List[Dict[str, float]] = []  # [{x, y}, ...]


class CompositionAnalysis(BaseModel):
    """LLM-generated composition analysis."""
    composition_type: str  # "symmetrical", "dynamic", "triangular", etc.
    balance_description: str
    visual_flow: str  # Description of how the eye moves
    focal_point_analysis: str
    spatial_depth: str  # Analysis of depth and perspective
    dynamism_level: str  # "static", "dynamic", "highly dynamic"
    source: str = "llm"


class SceneFeatures(BaseModel):
    """Extracted scene/semantic features."""
    detected_objects: List[str] = []  # From CLIP/BLIP/WD14
    style_tags: List[str] = []  # From tagger
    clip_description: Optional[str] = None  # CLIP Interrogator output
    detected_text: List[Dict[str, Any]] = []  # OCR results [{text, language, confidence, bbox}, ...]
    primary_subject: Optional[str] = None


class SceneAnalysis(BaseModel):
    """LLM-generated scene/semantic analysis."""
    narrative_interpretation: str  # Story/meaning interpretation
    symbolism: str  # Analysis of symbolic elements
    subject_analysis: str  # Analysis of depicted subjects
    text_interpretation: Optional[str] = None  # If text was detected
    cultural_references: List[str] = []
    source: str = "llm"


class TechniqueAnalysis(BaseModel):
    """LLM-generated technique/light/space analysis."""
    brushwork: str  # Analysis of brushwork/technique
    light_analysis: str  # Light source, quality, mood
    spatial_treatment: str  # How space is handled
    medium_estimation: str  # Estimated medium (oil, watercolor, etc.)
    technical_skill_indicators: List[str]
    source: str = "llm"


class HistoricalContextAnalysis(BaseModel):
    """LLM-generated historical context analysis."""
    estimated_era: str  # Estimated time period
    art_movement_connections: List[str]  # Connected art movements
    artistic_influences: str  # Detected influences
    historical_significance: str  # Place in art history
    cultural_context: str  # Cultural/historical context
    confidence_note: str  # Disclaimer about interpretation
    source: str = "llm"


class DeepAnalysisRequest(BaseModel):
    """Request for deep analysis."""
    module: Optional[str] = None  # "color", "composition", "scene", "technique", "historical", None for full
    image_path: str  # Path to already uploaded image


class InlineMarker(BaseModel):
    """Single inline marker extracted from summary text."""
    id: str
    type: str  # "color", "technique", "composition", "mood", "era", "artist"
    value: str  # The marker value (e.g., "#4f6b92" for color, "импасто" for technique)
    label: str  # Display label
    icon: str  # Icon name for frontend (palette, brush, layers, heart, clock, user)
    css_class: str  # CSS class for styling


class RichSummary(BaseModel):
    """Rich summary with parsed inline markers."""
    raw_text: str  # Original text with markers
    cleaned_text: str  # Text with markers replaced by placeholders
    html_text: str  # Text with HTML spans for markers
    markers: List[InlineMarker]  # Extracted markers
    marker_count: int  # Total number of markers


class DeepAnalysisModuleResponse(BaseModel):
    """Response for single module analysis."""
    success: bool = True
    module: str
    features: Optional[Dict[str, Any]] = None  # Raw extracted features
    analysis: Dict[str, Any]  # LLM interpretation
    message: Optional[str] = None


class DeepAnalysisFullResponse(BaseModel):
    """Full deep analysis response with all modules."""
    success: bool = True
    color: Optional[ColorPsychologyAnalysis] = None
    color_features: Optional[ColorFeatures] = None
    composition: Optional[CompositionAnalysis] = None
    composition_features: Optional[CompositionFeatures] = None
    scene: Optional[SceneAnalysis] = None
    scene_features: Optional[SceneFeatures] = None
    technique: Optional[TechniqueAnalysis] = None
    historical: Optional[HistoricalContextAnalysis] = None
    summary: Optional[RichSummary] = None  # Changed from str to RichSummary
    message: Optional[str] = None

