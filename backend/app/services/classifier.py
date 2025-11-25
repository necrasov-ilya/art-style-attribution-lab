"""Classifier service - calls ML module for predictions."""
import sys
from typing import Dict, Any

from app.core.config import settings


def get_full_predictions(image_path: str, top_k: int = 3) -> Dict[str, Any]:
    """
    Call the ML module to get full predictions (artists, genres, styles).
    
    Args:
        image_path: Path to the uploaded image
        top_k: Number of top predictions to return per category
        
    Returns:
        Dict with 'artists', 'genres', 'styles' lists
    """
    ml_dir = str(settings.ML_DIR)
    if ml_dir not in sys.path:
        sys.path.insert(0, ml_dir)
    
    from predict_artists import predict_full
    
    return predict_full(image_path, top_k=top_k)


def get_top_artists(image_path: str, top_k: int = 3):
    """Legacy function - returns only artists."""
    result = get_full_predictions(image_path, top_k)
    return result["artists"]
