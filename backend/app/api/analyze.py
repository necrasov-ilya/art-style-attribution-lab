"""Analyze API endpoint."""
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.models.history import AnalysisHistory
from app.models.schemas import (
    AnalysisResponse,
    ArtistPrediction,
    GenrePrediction,
    StylePrediction,
    GenerateRequest,
    GenerateResponse,
    GeneratedThumbnail,
    ErrorResponse,
)
from app.services.classifier import get_full_predictions
from app.services.llm_service import generate_explanation
from app.services.comfyui_service import generate_images_with_prompt

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
    db: Session = Depends(get_db),
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
        # Get full ML predictions (artists, genres, styles)
        # Uses ML_TOP_K and ML_INCLUDE_UNKNOWN_ARTIST from settings
        predictions = get_full_predictions(str(file_path))
        
        # Convert to Pydantic models
        top_artists = [
            ArtistPrediction(
                index=p["index"],
                artist_slug=p["artist_slug"],
                probability=p["probability"]
            )
            for p in predictions["artists"]
        ]
        
        top_genres = [
            GenrePrediction(
                index=p["index"],
                name=p["name"],
                probability=p["probability"]
            )
            for p in predictions["genres"]
        ]
        
        top_styles = [
            StylePrediction(
                index=p["index"],
                name=p["name"],
                probability=p["probability"]
            )
            for p in predictions["styles"]
        ]
        
        # Generate LLM explanation (async)
        explanation = await generate_explanation(top_artists, top_genres, top_styles)
        
        # Build response
        response = AnalysisResponse(
            success=True,
            image_path=f"/api/uploads/{unique_filename}",
            top_artists=top_artists,
            top_genres=top_genres,
            top_styles=top_styles,
            explanation=explanation,
            message="Analysis completed successfully"
        )
        
        # Save to history (skip for guest users)
        try:
            is_guest = False
            try:
                uname = (current_user.username or '').lower()
                email = (current_user.email or '').lower()
                if uname.startswith('guest_') or email.startswith('guest_'):
                    is_guest = True
            except Exception:
                is_guest = False

            if not is_guest:
                history_item = AnalysisHistory(
                    user_id=current_user.id,
                    image_filename=unique_filename,
                    image_url=f"/api/uploads/{unique_filename}",
                    top_artist_slug=top_artists[0].artist_slug if top_artists else "unknown",
                    top_artist_probability=f"{top_artists[0].probability:.3f}" if top_artists else None,
                    analysis_result=response.model_dump(),
                )
                db.add(history_item)
                db.commit()
        except Exception as save_error:
            # Don't fail the whole request if history save fails
            db.rollback()
            print(f"Warning: Failed to save to history: {save_error}")
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )


@router.post(
    "/generate",
    response_model=GenerateResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def generate_style_images(
    request: GenerateRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Generate images in a specific artistic style.
    
    Uses LLM to create a prompt based on the artist/style/genre,
    optionally incorporating user-provided details.
    Then uses ComfyUI to generate images.
    
    Args:
        request: Generation parameters including artist, style, genre, and optional user prompt
        
    Returns:
        Generated images with the prompt used
    """
    try:
        # Generate images using ComfyUI service
        result = await generate_images_with_prompt(
            artist_slug=request.artist_slug,
            style_name=request.style_name,
            genre_name=request.genre_name,
            user_details=request.user_prompt,
            count=request.count
        )
        
        return GenerateResponse(
            success=True,
            prompt=result["prompt"],
            images=[
                GeneratedThumbnail(
                    url=img["url"],
                    artist_slug=request.artist_slug,
                    prompt=result["prompt"]
                )
                for img in result["images"]
            ],
            message="Images generated successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Generation failed: {str(e)}"
        )
