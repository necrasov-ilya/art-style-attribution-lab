"""Analyze API endpoint."""
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.deps import get_current_user
from app.core.config import settings
from app.models.user import User
from app.models.schemas import (
    AnalysisResponse,
    ArtistPrediction,
    ErrorResponse,
)
from app.services.classifier import get_top_artists
from app.services.llm_service import generate_explanation
from app.services.comfyui_service import generate_thumbnails

router = APIRouter(tags=["Analysis"])

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/bmp"}


@router.post(
    "/analyze",
    response_model=AnalysisResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def analyze_image(
    file: UploadFile = File(..., description="Image file to analyze"),
    current_user: User = Depends(get_current_user),
):
    """
    Analyze an uploaded image to detect art style and predict similar artists.
    
    Requires authentication via Bearer token.
    
    Returns:
    - top_artists: Top 3 artist predictions with probabilities
    - explanation: LLM-generated explanation (currently stub)
    - generated_thumbnails: 4 generated images in detected styles (currently stub)
    """
    # Validate file extension
    file_ext = Path(file.filename).suffix.lower() if file.filename else ""
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Validate content type
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid content type: {file.content_type}"
        )
    
    # Read file content
    content = await file.read()
    
    # Check file size
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE // (1024*1024)}MB"
        )
    
    # Generate unique filename and save
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = settings.UPLOAD_DIR / unique_filename
    
    try:
        with open(file_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )
    
    try:
        # Get ML predictions
        predictions = get_top_artists(str(file_path), top_k=3)
        
        # Convert to Pydantic models (predictions are dicts)
        top_artists = [
            ArtistPrediction(
                index=p["index"],
                artist_slug=p["artist_slug"],
                probability=p["probability"]
            )
            for p in predictions
        ]
        
        # Generate explanation (stub)
        explanation = generate_explanation(top_artists)
        
        # Generate thumbnails (stub)
        thumbnails = generate_thumbnails(top_artists, count=4)
        
        return AnalysisResponse(
            success=True,
            image_path=str(file_path),
            top_artists=top_artists,
            explanation=explanation,
            generated_thumbnails=thumbnails,
            message="Analysis completed successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )
