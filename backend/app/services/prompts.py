"""Prompt templates for LLM-based art analysis explanations.

This module contains all prompt templates used by the LLM service.
Prompts are centralized here for easy maintenance and versioning.
"""

# System prompt defines the role and behavior of the LLM
SYSTEM_PROMPT = """You are an expert art historian and critic with deep knowledge of artistic styles, techniques, and art history. 

Your task is to provide insightful, educational analysis of artworks based on ML classification results. 
Be concise but informative. Focus on specific visual elements that connect the artwork to identified styles and artists.

Guidelines:
- Use professional but accessible language
- Reference specific artistic techniques (brushwork, composition, color palette, etc.)
- Provide historical context when relevant
- Be confident but acknowledge uncertainty when probabilities are low
- Keep responses under 200 words"""


def build_analysis_prompt(
    artists: list[dict],
    genres: list[dict],
    styles: list[dict]
) -> str:
    """Build the user prompt for art analysis explanation.
    
    Args:
        artists: List of dicts with keys: name, probability
        genres: List of dicts with keys: name, probability  
        styles: List of dicts with keys: name, probability
        
    Returns:
        Formatted prompt string for the LLM
    """
    # Format artists section
    artists_text = "\n".join([
        f"  - {a['name']}: {a['probability']:.1%} confidence"
        for a in artists
    ]) if artists else "  No artists identified"
    
    # Format genres section  
    genres_text = "\n".join([
        f"  - {g['name']}: {g['probability']:.1%} confidence"
        for g in genres
    ]) if genres else "  No genres identified"
    
    # Format styles section
    styles_text = "\n".join([
        f"  - {s['name']}: {s['probability']:.1%} confidence"
        for s in styles
    ]) if styles else "  No styles identified"
    
    prompt = f"""Analyze the following ML classification results for an artwork and provide a concise, insightful summary.

CLASSIFICATION RESULTS:

Artists (stylistic similarity):
{artists_text}

Genres:
{genres_text}

Artistic Styles:
{styles_text}

Based on these results, provide:
1. A brief interpretation of what these classifications tell us about the artwork
2. Key visual characteristics that likely contributed to these classifications
3. Historical/artistic context connecting the identified elements

Keep your response focused and under 200 words."""

    return prompt


def format_prediction_for_prompt(prediction: dict) -> dict:
    """Convert a prediction object to prompt-friendly format.
    
    Args:
        prediction: Dict with index, name/artist_slug, probability
        
    Returns:
        Dict with name and probability for prompt building
    """
    name = prediction.get("name") or prediction.get("artist_slug", "Unknown")
    # Clean up name formatting
    name = name.replace("-", " ").replace("_", " ").title()
    
    return {
        "name": name,
        "probability": prediction.get("probability", 0.0)
    }
