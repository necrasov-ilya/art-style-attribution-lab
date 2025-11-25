"""LLM service - generates explanations for art analysis results.

This module provides the high-level interface for generating LLM explanations.
It uses the llm_client for provider abstraction and prompts module for templates.
"""
import logging
from typing import List

from app.models.schemas import (
    ArtistPrediction, 
    GenrePrediction,
    StylePrediction, 
    AnalysisExplanation
)
from app.services.llm_client import get_cached_provider, LLMError
from app.services.prompts import (
    SYSTEM_PROMPT,
    build_analysis_prompt,
    format_prediction_for_prompt
)
from app.core.config import settings

logger = logging.getLogger(__name__)


async def generate_explanation(
    top_artists: List[ArtistPrediction],
    top_genres: List[GenrePrediction] = None,
    top_styles: List[StylePrediction] = None
) -> AnalysisExplanation:
    """
    Generate an LLM-powered explanation for the art style prediction.
    
    Args:
        top_artists: List of artist predictions
        top_genres: List of genre predictions
        top_styles: List of style predictions
        
    Returns:
        AnalysisExplanation with text and source indicator
    """
    if not top_artists:
        return AnalysisExplanation(
            text="No artists detected in the image.",
            source="stub"
        )
    
    # Convert predictions to prompt-friendly format
    artists_data = [
        format_prediction_for_prompt({
            "artist_slug": a.artist_slug,
            "probability": a.probability
        })
        for a in top_artists
    ]
    
    genres_data = [
        format_prediction_for_prompt({
            "name": g.name,
            "probability": g.probability
        })
        for g in (top_genres or [])
    ]
    
    styles_data = [
        format_prediction_for_prompt({
            "name": s.name,
            "probability": s.probability
        })
        for s in (top_styles or [])
    ]
    
    # Build the prompt
    user_prompt = build_analysis_prompt(artists_data, genres_data, styles_data)
    
    # Get LLM provider and generate
    try:
        provider = get_cached_provider()
        
        # Check if using stub provider
        if settings.LLM_PROVIDER.lower() == "none":
            # Return formatted stub response
            return _build_stub_explanation(top_artists, top_genres, top_styles)
        
        response = await provider.generate(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=settings.LLM_MAX_TOKENS,
            temperature=settings.LLM_TEMPERATURE
        )
        
        return AnalysisExplanation(
            text=response,
            source=settings.LLM_PROVIDER
        )
        
    except LLMError as e:
        logger.error(f"LLM generation failed: {e}")
        # Fallback to stub on error
        explanation = _build_stub_explanation(top_artists, top_genres, top_styles)
        explanation.text += f"\n\n[LLM unavailable: {str(e)}]"
        return explanation


def _build_stub_explanation(
    top_artists: List[ArtistPrediction],
    top_genres: List[GenrePrediction] = None,
    top_styles: List[StylePrediction] = None
) -> AnalysisExplanation:
    """Build a stub explanation when LLM is not available."""
    top_artist = top_artists[0]
    artist_name = top_artist.artist_slug.replace("-", " ").title()
    probability_pct = round(top_artist.probability * 100, 1)
    
    # Build style info
    style_text = ""
    if top_styles and len(top_styles) > 0:
        top_style = top_styles[0]
        style_name = top_style.name.replace("_", " ").title()
        style_text = f" The artistic style is most closely aligned with {style_name}."
    
    # Build genre info
    genre_text = ""
    if top_genres and len(top_genres) > 0:
        top_genre = top_genres[0]
        genre_name = top_genre.name.replace("_", " ").title()
        genre_text = f" The genre appears to be {genre_name}."
    
    # Other artists
    other_artists = ""
    if len(top_artists) > 1:
        other_names = [a.artist_slug.replace("-", " ").title() for a in top_artists[1:]]
        other_artists = f" Other possible influences include {', '.join(other_names)}."
    
    explanation_text = (
        f"Based on the analysis, this artwork shows stylistic similarities "
        f"to the work of {artist_name} ({probability_pct}% confidence).{style_text}{genre_text}"
        f"{other_artists}"
    )
    
    return AnalysisExplanation(
        text=explanation_text,
        source="stub"
    )
