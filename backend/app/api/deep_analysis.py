"""Deep Analysis API endpoints."""
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_current_user
from app.core.config import settings
from app.models.user import User
from app.models.schemas import (
    DeepAnalysisModuleResponse,
    DeepAnalysisFullResponse,
    ErrorResponse,
)
from app.services.deep_analysis_service import (
    run_single_module_analysis,
    run_full_deep_analysis,
)
from app.services.classifier import get_full_predictions

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/deep-analysis", tags=["Deep Analysis"])

VALID_MODULES = {"color", "composition", "scene", "technique", "historical"}


def resolve_image_path(image_path: str) -> str:
    """Resolve image path from API path to filesystem path."""
    # Handle /api/uploads/filename.jpg format
    if image_path.startswith("/api/uploads/"):
        filename = image_path.replace("/api/uploads/", "")
        full_path = settings.UPLOAD_DIR / filename
    elif image_path.startswith("uploads/"):
        filename = image_path.replace("uploads/", "")
        full_path = settings.UPLOAD_DIR / filename
    else:
        # Assume it's already a filename or full path
        full_path = Path(image_path)
        if not full_path.is_absolute():
            full_path = settings.UPLOAD_DIR / image_path
    
    if not full_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image not found: {image_path}"
        )
    
    return str(full_path)


@router.get(
    "/module/{module}",
    response_model=DeepAnalysisModuleResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def analyze_single_module(
    module: str,
    image_path: str = Query(..., description="Path to the image (from /api/uploads/...)"),
    current_user: User = Depends(get_current_user),
):
    """
    Run a single deep analysis module on an image.
    
    Available modules:
    - **color**: Color psychology analysis (dominant colors, mood, harmony)
    - **composition**: Composition analysis (rule of thirds, balance, focal points)
    - **scene**: Scene/semantic analysis (narrative, symbolism, subjects)
    - **technique**: Technical analysis (brushwork, light, medium)
    - **historical**: Historical context (era, influences, art movements)
    
    Each module extracts visual features and uses LLM for interpretation.
    """
    if module not in VALID_MODULES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid module. Valid options: {', '.join(VALID_MODULES)}"
        )
    
    try:
        resolved_path = resolve_image_path(image_path)
        
        # Get ML predictions for context
        ml_predictions = None
        try:
            ml_predictions = get_full_predictions(resolved_path, top_k=3)
        except Exception as e:
            logger.warning(f"Could not get ML predictions: {e}")
        
        # Run single module analysis
        result = await run_single_module_analysis(module, resolved_path, ml_predictions)
        
        return DeepAnalysisModuleResponse(
            success=True,
            module=module,
            features=result.get("features"),
            analysis=result.get("analysis", {}),
            message=f"Модуль '{module}' успешно выполнен"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Deep analysis module '{module}' failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )


@router.get(
    "/full",
    response_model=DeepAnalysisFullResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def run_full_analysis(
    image_path: str = Query(..., description="Path to the image (from /api/uploads/...)"),
    current_user: User = Depends(get_current_user),
):
    """
    Run complete deep analysis with all modules.
    
    This endpoint implements a "deep research" pattern similar to Gemini Deep Research
    or ChatGPT Deep Research. It makes multiple sequential LLM calls:
    
    1. **Feature Extraction**: Color, composition, scene features (parallel)
    2. **Color Psychology**: Emotional interpretation of palette
    3. **Composition Analysis**: Structure, balance, visual flow
    4. **Scene Analysis**: Narrative, symbolism, subjects
    5. **Technique Analysis**: Brushwork, light, medium estimation
    6. **Historical Context**: Era, influences, art movement connections
    7. **Summary Synthesis**: Final cohesive interpretation
    
    Each step builds on previous results for comprehensive analysis.
    """
    try:
        resolved_path = resolve_image_path(image_path)
        
        # Get ML predictions for context
        ml_predictions = None
        try:
            ml_predictions = get_full_predictions(resolved_path, top_k=3)
        except Exception as e:
            logger.warning(f"Could not get ML predictions: {e}")
        
        # Run full deep analysis
        result = await run_full_deep_analysis(resolved_path, ml_predictions)
        
        return DeepAnalysisFullResponse(
            success=True,
            color=result.get("color"),
            color_features=result.get("color_features"),
            composition=result.get("composition"),
            composition_features=result.get("composition_features"),
            scene=result.get("scene"),
            scene_features=result.get("scene_features"),
            technique=result.get("technique"),
            historical=result.get("historical"),
            summary=result.get("summary"),
            message="Полный глубокий анализ завершён"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Full deep analysis failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )


@router.get(
    "/features/color",
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def get_color_features(
    image_path: str = Query(..., description="Path to the image"),
    current_user: User = Depends(get_current_user),
):
    """
    Extract color features without LLM interpretation.
    
    Returns raw color data:
    - Dominant colors (7) with hex, RGB, LAB values
    - Warm/cool ratio
    - Overall contrast and saturation
    - Brightness
    
    Useful for visualization or custom processing.
    """
    from app.services.deep_analysis_service import extract_color_features
    
    try:
        resolved_path = resolve_image_path(image_path)
        features = extract_color_features(resolved_path)
        
        return {
            "success": True,
            "features": features
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Color feature extraction failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Feature extraction failed: {str(e)}"
        )


@router.get(
    "/features/composition",
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def get_composition_features(
    image_path: str = Query(..., description="Path to the image"),
    current_user: User = Depends(get_current_user),
):
    """
    Extract composition features without LLM interpretation.
    
    Returns raw composition data:
    - Saliency center coordinates
    - Rule of thirds alignment score
    - Symmetry scores (horizontal/vertical)
    - Focal points with coordinates and strength
    - Visual weight distribution
    - Perspective detection
    """
    from app.services.deep_analysis_service import extract_composition_features
    
    try:
        resolved_path = resolve_image_path(image_path)
        features = extract_composition_features(resolved_path)
        
        return {
            "success": True,
            "features": features
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Composition feature extraction failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Feature extraction failed: {str(e)}"
        )
