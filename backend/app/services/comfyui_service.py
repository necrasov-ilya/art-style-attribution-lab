"""ComfyUI service - stub for generating images."""
from typing import List
from app.models.schemas import ArtistPrediction, GeneratedThumbnail


def generate_thumbnails(top_artists: List[ArtistPrediction], count: int = 4) -> List[GeneratedThumbnail]:
    """
    Generate image thumbnails in the style of detected artists.
    
    Currently a stub - will be replaced with actual ComfyUI integration.
    
    Args:
        top_artists: List of top artist predictions
        count: Number of thumbnails to generate
        
    Returns:
        List of GeneratedThumbnail objects
    """
    thumbnails = []
    
    # Placeholder image URLs (using picsum.photos for demo)
    placeholder_images = [
        "https://picsum.photos/seed/art1/256/256",
        "https://picsum.photos/seed/art2/256/256",
        "https://picsum.photos/seed/art3/256/256",
        "https://picsum.photos/seed/art4/256/256",
    ]
    
    for i in range(min(count, len(placeholder_images))):
        # Cycle through artists for prompts
        artist_idx = i % len(top_artists) if top_artists else 0
        artist_slug = top_artists[artist_idx].artist_slug if top_artists else "unknown"
        artist_name = artist_slug.replace("-", " ").title()
        
        thumbnails.append(GeneratedThumbnail(
            url=placeholder_images[i],
            artist_slug=artist_slug,
            prompt=f"A painting in the style of {artist_name} [ComfyUI stub]"
        ))
    
    return thumbnails
