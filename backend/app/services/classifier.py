"""Classifier service - calls ML module for predictions."""
import sys
from typing import List, Dict, Any

from app.core.config import settings


def get_top_artists(image_path: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """
    Call the ML module to get top-k artist predictions.
    
    Args:
        image_path: Path to the uploaded image
        top_k: Number of top predictions to return
        
    Returns:
        List of dicts with index, artist_slug, probability
    """
    ml_dir = str(settings.ML_DIR)
    if ml_dir not in sys.path:
        sys.path.insert(0, ml_dir)
    
    from predict_artists import predict_top_artists
    
    predictions = predict_top_artists(image_path, top_k=top_k)
    
    return predictions
