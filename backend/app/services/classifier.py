"""Classifier service - calls ML module for predictions."""
import sys
from pathlib import Path
from typing import List, Tuple

from app.core.config import settings


def get_top_artists(image_path: str, top_k: int = 3) -> List[Tuple[int, str, float]]:
    """
    Call the ML module to get top-k artist predictions.
    
    Args:
        image_path: Path to the uploaded image
        top_k: Number of top predictions to return
        
    Returns:
        List of tuples (index, artist_slug, probability)
    """
    # Add ML directory to path
    ml_dir = str(settings.ML_DIR)
    if ml_dir not in sys.path:
        sys.path.insert(0, ml_dir)
    
    # Import the prediction function
    from predict_artists import predict_top_artists
    
    # Get predictions
    predictions = predict_top_artists(image_path, k=top_k)
    
    return predictions
