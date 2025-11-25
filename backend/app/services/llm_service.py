"""LLM service - stub for generating explanations."""
from typing import List
from app.models.schemas import ArtistPrediction, AnalysisExplanation


def generate_explanation(top_artists: List[ArtistPrediction]) -> AnalysisExplanation:
    """
    Generate an explanation for the art style prediction.
    
    Currently a stub - will be replaced with actual LLM call.
    
    Args:
        top_artists: List of top artist predictions
        
    Returns:
        AnalysisExplanation with text and source
    """
    if not top_artists:
        return AnalysisExplanation(
            text="No artists detected in the image.",
            source="stub"
        )
    
    # Create stub explanation based on predictions
    top_artist = top_artists[0]
    artist_name = top_artist.artist_slug.replace("-", " ").title()
    probability_pct = round(top_artist.probability * 100, 1)
    
    other_artists = ""
    if len(top_artists) > 1:
        other_names = [a.artist_slug.replace("-", " ").title() for a in top_artists[1:]]
        other_artists = f" Other possible influences include {', '.join(other_names)}."
    
    explanation_text = (
        f"Based on the analysis, this artwork shows strong stylistic similarities "
        f"to the work of {artist_name} with {probability_pct}% confidence. "
        f"The composition, color palette, and brushwork techniques are characteristic "
        f"of this artist's distinctive style.{other_artists} "
        f"[This is a placeholder explanation - LLM integration coming soon.]"
    )
    
    return AnalysisExplanation(
        text=explanation_text,
        source="stub"
    )
