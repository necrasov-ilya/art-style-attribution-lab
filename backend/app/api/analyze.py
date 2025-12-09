"""Analyze API endpoint."""
import json
import logging
import uuid
from pathlib import Path
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limiter import concurrent_limiter, rate_limiter
from app.core.file_validator import validate_image_upload
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
    AnalysisExplanation,
)
from app.services.classifier import get_full_predictions
from app.services.llm_service import (
    generate_explanation,
    analyze_unknown_artist_with_vision,
    generate_explanation_streaming,
)
from app.services.comfyui_service import generate_images_with_prompt

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Analysis"])

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/bmp"}


@router.post(
    "/analyze",
    response_model=AnalysisResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def analyze_image(
    request: Request,
    file: UploadFile = File(..., description="Image file to analyze"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Analyze an uploaded image to detect art style and predict similar artists.

    Requires authentication via Bearer token.
    Rate limited to 10 requests per minute.
    Cannot run simultaneously with generation or deep analysis.

    Returns:
    - top_artists: Top 3 artist predictions with probabilities
    - explanation: LLM-generated explanation (currently stub)
    - generated_thumbnails: 4 generated images in detected styles (currently stub)
    """
    # Check rate limit
    await rate_limiter.check_rate_limit(current_user.id, request.url.path)

    # Acquire concurrent operation lock
    await concurrent_limiter.acquire(current_user.id, "analyze")

    try:
        # Validate uploaded file (extension, content-type, size, magic numbers)
        content = await validate_image_upload(file, settings.MAX_UPLOAD_SIZE)

        # Get file extension for saving
        file_ext = Path(file.filename).suffix.lower() if file.filename else ".jpg"

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

        # Get full ML predictions (artists, genres, styles)
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

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )
    finally:
        # Always release the lock
        await concurrent_limiter.release(current_user.id, "analyze")


@router.post("/analyze/stream")
async def analyze_image_stream(
    request: Request,
    file: UploadFile = File(..., description="Image file to analyze"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Analyze image with Server-Sent Events (SSE) for real-time streaming.
    
    Events sent:
    - predictions: ML results (artists, genres, styles) - sent immediately after ML analysis
    - vision: Vision AI analysis result (only for Unknown Artist)
    - text: Streaming chunks of LLM explanation
    - complete: Final completion with full result
    - error: If something goes wrong
    
    Flow:
    1. ML analysis → send 'predictions' event
    2. If Unknown Artist → Vision analysis → send 'vision' event  
    3. Stream LLM explanation → send 'text' events
    4. Save to history → send 'complete' event
    """
    # Check rate limit
    await rate_limiter.check_rate_limit(current_user.id, request.url.path)
    
    # Acquire lock
    await concurrent_limiter.acquire(current_user.id, "analyze")
    
    async def event_generator() -> AsyncGenerator[str, None]:
        unique_filename = None
        try:
            # Validate and save file
            content = await validate_image_upload(file, settings.MAX_UPLOAD_SIZE)
            file_ext = Path(file.filename).suffix.lower() if file.filename else ".jpg"
            unique_filename = f"{uuid.uuid4()}{file_ext}"
            file_path = settings.UPLOAD_DIR / unique_filename
            
            with open(file_path, "wb") as f:
                f.write(content)
            
            # ML predictions
            predictions = get_full_predictions(str(file_path))
            
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
            
            # Check if Unknown Artist
            is_unknown = False
            vision_result = None
            top_artist_slug = top_artists[0].artist_slug.lower() if top_artists else ""
            
            if "unknown" in top_artist_slug or top_artist_slug in ["unknown-artist", "unknown_artist"]:
                is_unknown = True
            
            # Send predictions event (but mark if we need vision analysis)
            predictions_data = {
                "image_path": f"/api/uploads/{unique_filename}",
                "top_artists": [a.model_dump() for a in top_artists],
                "top_genres": [g.model_dump() for g in top_genres],
                "top_styles": [s.model_dump() for s in top_styles],
                "needs_vision": is_unknown,
            }
            yield f"event: predictions\ndata: {json.dumps(predictions_data, ensure_ascii=False)}\n\n"
            
            # If Unknown Artist, run Vision analysis
            if is_unknown and settings.VISION_LLM_ENABLED:
                vision_result = await analyze_unknown_artist_with_vision(str(file_path))
                
                # Check if it's a photo
                is_photo = vision_result.get("is_photo", False)
                
                # Send vision event
                vision_data = {
                    "is_photo": is_photo,
                    "artist_name": vision_result.get("artist_name"),
                    "artist_name_ru": vision_result.get("artist_name_ru"),
                    "confidence": vision_result.get("confidence", "none"),
                    "reasoning": vision_result.get("reasoning"),
                    "artwork_description": vision_result.get("artwork_description"),
                }
                yield f"event: vision\ndata: {json.dumps(vision_data, ensure_ascii=False)}\n\n"
                
                # If Vision identified an artist with confidence, update prediction
                if vision_result.get("artist_name") and vision_result.get("confidence") in ["high", "medium"]:
                    artist_slug = vision_result["artist_name"].lower().replace(" ", "-")
                    top_artists[0] = ArtistPrediction(
                        index=-1,  # Special index for Vision-identified
                        artist_slug=artist_slug,
                        probability=0.0  # Will use Vision confidence instead
                    )
            
            # Stream LLM explanation
            full_explanation = ""
            async for chunk in generate_explanation_streaming(
                top_artists=top_artists,
                top_genres=top_genres,
                top_styles=top_styles,
                vision_context=vision_result
            ):
                full_explanation += chunk
                yield f"event: text\ndata: {json.dumps({'chunk': chunk}, ensure_ascii=False)}\n\n"
            
            # Save to history
            is_guest = False
            try:
                uname = (current_user.username or '').lower()
                email = (current_user.email or '').lower()
                if uname.startswith('guest_') or email.startswith('guest_'):
                    is_guest = True
            except:
                pass
            
            history_id = None
            if not is_guest and unique_filename:
                try:
                    response_data = {
                        "success": True,
                        "image_path": f"/api/uploads/{unique_filename}",
                        "top_artists": [a.model_dump() for a in top_artists],
                        "top_genres": [g.model_dump() for g in top_genres],
                        "top_styles": [s.model_dump() for s in top_styles],
                        "explanation": {"text": full_explanation, "source": settings.LLM_PROVIDER},
                        "vision_result": vision_result,
                    }
                    
                    history_item = AnalysisHistory(
                        user_id=current_user.id,
                        image_filename=unique_filename,
                        image_url=f"/api/uploads/{unique_filename}",
                        top_artist_slug=top_artists[0].artist_slug if top_artists else "unknown",
                        top_artist_probability=f"{top_artists[0].probability:.3f}" if top_artists else None,
                        analysis_result=response_data,
                    )
                    db.add(history_item)
                    db.commit()
                    history_id = history_item.id
                except Exception as e:
                    db.rollback()
                    logger.warning(f"Failed to save history: {e}")
            
            # Send complete event
            complete_data = {
                "success": True,
                "history_id": history_id,
                "explanation_source": settings.LLM_PROVIDER,
            }
            yield f"event: complete\ndata: {json.dumps(complete_data, ensure_ascii=False)}\n\n"
            
        except HTTPException as e:
            yield f"event: error\ndata: {json.dumps({'error': e.detail}, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error(f"Stream analysis error: {e}", exc_info=True)
            yield f"event: error\ndata: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
        finally:
            await concurrent_limiter.release(current_user.id, "analyze")
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.post(
    "/generate",
    response_model=GenerateResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def generate_style_images(
    http_request: Request,
    request: GenerateRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Generate images in a specific artistic style.

    Uses LLM to create a prompt based on the artist/style/genre,
    optionally incorporating user-provided details.
    Then uses ComfyUI to generate images.

    Rate limited to 5 requests per minute.
    Cannot run simultaneously with analysis or deep analysis.

    Args:
        request: Generation parameters including artist, style, genre, and optional user prompt

    Returns:
        Generated images with the prompt used
    """
    # Check rate limit
    await rate_limiter.check_rate_limit(current_user.id, http_request.url.path)

    # Acquire concurrent operation lock
    await concurrent_limiter.acquire(current_user.id, "generate")

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

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Generation failed: {str(e)}"
        )
    finally:
        # Always release the lock
        await concurrent_limiter.release(current_user.id, "generate")
