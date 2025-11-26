"""Classifier service - calls ML module for predictions."""
import sys
from typing import Dict, Any

from app.core.config import settings


def get_full_predictions(image_path: str, top_k: int = None) -> Dict[str, Any]:
    """
    Call the ML module to get full predictions (artists, genres, styles).
    
    Args:
        image_path: Path to the uploaded image
        top_k: Number of top predictions to return per category.
               If None, uses settings.ML_TOP_K
        
    Returns:
        Dict with 'artists', 'genres', 'styles' lists
    """
    ml_dir = str(settings.ML_DIR)
    if ml_dir not in sys.path:
        sys.path.insert(0, ml_dir)
    
    from predict_artists import predict_full
    
    # Use settings if top_k not specified
    if top_k is None:
        top_k = settings.ML_TOP_K
    
    return predict_full(
        image_path, 
        top_k=top_k,
        include_unknown_artist=settings.ML_INCLUDE_UNKNOWN_ARTIST
    )


def get_top_artists(image_path: str, top_k: int = None):
    """Legacy function - returns only artists."""
    result = get_full_predictions(image_path, top_k)
    return result["artists"]
