"""LLM service - stub for generating explanations."""
from typing import List
from app.models.schemas import ArtistPrediction, StylePrediction, AnalysisExplanation


def generate_explanation(
    top_artists: List[ArtistPrediction],
    top_styles: List[StylePrediction] = None
) -> AnalysisExplanation:
    """
    Generate an explanation for the art style prediction.
    
    Currently a stub - will be replaced with actual LLM call.
    """
    if not top_artists:
        return AnalysisExplanation(
            text="No artists detected in the image.",
            source="stub"
        )
    
    top_artist = top_artists[0]
    artist_name = top_artist.artist_slug.replace("-", " ").title()
    probability_pct = round(top_artist.probability * 100, 1)
    
    # Build style info
    style_text = ""
    if top_styles and len(top_styles) > 0:
        top_style = top_styles[0]
        style_name = top_style.name.replace("_", " ")
        style_text = f" The artistic style is most closely aligned with {style_name}."
    
    # Other artists
    other_artists = ""
    if len(top_artists) > 1:
        other_names = [a.artist_slug.replace("-", " ").title() for a in top_artists[1:]]
        other_artists = f" Other possible influences include {', '.join(other_names)}."
    
    explanation_text = (
        f"Based on the analysis, this artwork shows strong stylistic similarities "
        f"to the work of {artist_name} with {probability_pct}% confidence.{style_text} "
        f"The composition, color palette, and brushwork techniques are characteristic "
        f"of this artist's distinctive style.{other_artists} "
        f"[This is a placeholder explanation - LLM integration coming soon.]"
    )
    
    return AnalysisExplanation(
        text=explanation_text,
        source="stub"
    )
