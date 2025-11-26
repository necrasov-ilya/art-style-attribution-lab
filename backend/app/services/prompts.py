"""Prompt templates for LLM-based art analysis explanations.

This module contains all prompt templates used by the LLM service.
Prompts are centralized here for easy maintenance and versioning.
"""

# System prompt defines the role and behavior of the LLM
SYSTEM_PROMPT = """You are an expert art historian. Respond ONLY in Russian with Markdown formatting (##, ###, -, **). Maximum 250 words.

Format:
## 🎨 Художественный анализ
[1-2 sentences about main similarity]

### Ключевые характеристики
- **Техника**: [technique]
- **Палитра**: [colors]
- **Композиция**: [composition]

### Влияние мастеров
**[Artist 1]** (XX%): [similarity]
**[Artist 2]** (XX%): [similarity]
**[Artist 3]** (XX%): [similarity]

### Историко-художественный контекст
[1-2 sentences about style/era]"""


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
    # Format artists section with emphasis on all 3
    artists_text = ""
    for i, a in enumerate(artists[:3], 1):
        artists_text += f"  {i}. **{a['name']}** — уверенность {a['probability']:.1%}\n"
    if not artists_text:
        artists_text = "  Художники не определены"
    
    # Format genres section  
    genres_text = "\n".join([
        f"  - {g['name']}: {g['probability']:.1%}"
        for g in genres[:2]
    ]) if genres else "  Жанр не определён"
    
    # Format styles section
    styles_text = "\n".join([
        f"  - {s['name']}: {s['probability']:.1%}"
        for s in styles[:2]
    ]) if styles else "  Стиль не определён"
    
    prompt = f"""Analyze ML classification results for artwork. Respond in Russian with Markdown.

ARTISTS (mention ALL THREE):
{artists_text}
GENRES: {genres_text}
STYLES: {styles_text}

Follow the format from system prompt. Max 250 words."""

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


# ============ ComfyUI Image Generation Prompts ============

# System prompt for SD prompt generation - concise and direct
IMAGE_GEN_SYSTEM_PROMPT = """You are a Stable Diffusion prompt generator. Output ONLY a comma-separated English prompt (80-120 words) with: subject, artistic techniques, colors, lighting, mood, quality tags. No explanations."""

# System prompt when user provides their own idea
IMAGE_GEN_WITH_DETAILS_PROMPT = """You are a Stable Diffusion prompt generator. Translate user's idea to English if needed. Output ONLY a comma-separated English prompt (80-120 words) preserving user's concept, adding: artistic techniques, colors, lighting, quality tags. No explanations."""


# ============ Style Knowledge Base ============
# Detailed descriptions for artistic styles, genres, and techniques

STYLE_DETAILS = {
    # Art Movements/Styles
    "impressionism": {
        "techniques": "visible brushstrokes, broken color, optical mixing, en plein air, capturing light",
        "colors": "vibrant complementary colors, pure pigments, light-filled palette",
        "mood": "fleeting moments, atmospheric effects, natural light, outdoor scenes",
        "artists_ref": "Monet, Renoir, Degas style"
    },
    "post_impressionism": {
        "techniques": "bold brushwork, expressive color, geometric forms, thick impasto",
        "colors": "intense saturated colors, emotional color choices, non-naturalistic palette",
        "mood": "emotional depth, symbolic meaning, personal expression",
        "artists_ref": "Van Gogh, Cézanne, Gauguin style"
    },
    "expressionism": {
        "techniques": "distorted forms, aggressive brushwork, exaggerated lines, emotional intensity",
        "colors": "jarring color combinations, bold contrasts, non-realistic colors",
        "mood": "psychological tension, inner turmoil, dramatic emotion",
        "artists_ref": "Munch, Kirchner, Kandinsky style"
    },
    "cubism": {
        "techniques": "fragmented forms, multiple viewpoints, geometric shapes, flattened perspective",
        "colors": "muted earth tones, monochromatic sections, analytical palette",
        "mood": "intellectual deconstruction, abstract representation",
        "artists_ref": "Picasso, Braque style"
    },
    "surrealism": {
        "techniques": "dreamlike imagery, unexpected juxtapositions, precise realistic rendering of impossible scenes",
        "colors": "vivid dream colors, mysterious shadows, ethereal lighting",
        "mood": "subconscious exploration, dream logic, uncanny atmosphere",
        "artists_ref": "Dalí, Magritte, Ernst style"
    },
    "romanticism": {
        "techniques": "dramatic compositions, rich textures, expressive brushwork, sublime landscapes",
        "colors": "deep rich colors, warm golden light, dramatic contrasts",
        "mood": "emotional intensity, awe of nature, heroic grandeur",
        "artists_ref": "Turner, Friedrich, Delacroix style"
    },
    "baroque": {
        "techniques": "chiaroscuro lighting, dynamic composition, rich detail, dramatic poses",
        "colors": "deep shadows, golden highlights, rich jewel tones",
        "mood": "theatrical drama, religious fervor, opulent grandeur",
        "artists_ref": "Caravaggio, Rembrandt, Rubens style"
    },
    "renaissance": {
        "techniques": "linear perspective, sfumato, balanced composition, anatomical precision",
        "colors": "harmonious earth tones, subtle gradations, balanced palette",
        "mood": "idealized beauty, classical harmony, humanist dignity",
        "artists_ref": "Leonardo, Michelangelo, Raphael style"
    },
    "art_nouveau": {
        "techniques": "flowing organic lines, decorative patterns, flat color areas, stylized natural forms",
        "colors": "muted pastels, gold accents, nature-inspired palette",
        "mood": "elegant beauty, organic harmony, decorative refinement",
        "artists_ref": "Mucha, Klimt style"
    },
    "realism": {
        "techniques": "accurate observation, detailed rendering, naturalistic lighting, precise draftsmanship",
        "colors": "true-to-life colors, subtle tonal variations, natural palette",
        "mood": "objective truth, everyday life, social observation",
        "artists_ref": "Courbet, Millet style"
    },
    "abstract_expressionism": {
        "techniques": "gestural brushwork, action painting, large scale, spontaneous marks",
        "colors": "bold primary colors, dynamic contrasts, emotional color fields",
        "mood": "raw emotion, spontaneous expression, existential depth",
        "artists_ref": "Pollock, Rothko, de Kooning style"
    },
    "minimalism": {
        "techniques": "geometric forms, clean lines, solid colors, precise edges",
        "colors": "limited palette, pure colors, stark contrasts",
        "mood": "serene simplicity, meditative calm, essential forms",
        "artists_ref": "Judd, Flavin style"
    },
    "pop_art": {
        "techniques": "bold outlines, flat colors, Ben-Day dots, commercial imagery",
        "colors": "bright primary colors, high contrast, advertising palette",
        "mood": "ironic commentary, popular culture, mass media",
        "artists_ref": "Warhol, Lichtenstein style"
    },
    "symbolism": {
        "techniques": "dreamlike imagery, allegory, mysterious atmosphere, decorative elements",
        "colors": "muted mysterious tones, twilight palette, ethereal hues",
        "mood": "mystical meaning, spiritual depth, poetic mystery",
        "artists_ref": "Moreau, Redon style"
    },
    "pointillism": {
        "techniques": "small dots of pure color, optical mixing, systematic application",
        "colors": "pure spectrum colors, complementary dot patterns, luminous effect",
        "mood": "scientific precision, shimmering light, vibrant surfaces",
        "artists_ref": "Seurat, Signac style"
    },
    "fauvism": {
        "techniques": "wild brushwork, non-naturalistic color, simplified forms",
        "colors": "explosive vivid colors, clashing combinations, pure tube colors",
        "mood": "joyful exuberance, primitive energy, bold expression",
        "artists_ref": "Matisse, Derain style"
    },
    "ukiyo_e": {
        "techniques": "flat areas of color, bold outlines, decorative patterns, woodblock print style",
        "colors": "vibrant limited palette, careful color gradients",
        "mood": "floating world, elegant beauty, narrative scenes",
        "artists_ref": "Hokusai, Hiroshige style"
    },
}

GENRE_DETAILS = {
    "portrait": {
        "elements": "human face, expressive eyes, character study, psychological depth",
        "composition": "focus on subject, careful lighting on face, meaningful background"
    },
    "landscape": {
        "elements": "natural scenery, sky and land, atmospheric perspective, seasons",
        "composition": "horizon line, depth through layers, leading lines in nature"
    },
    "still_life": {
        "elements": "arranged objects, flowers, fruits, household items, symbolic objects",
        "composition": "careful arrangement, dramatic lighting, surface textures"
    },
    "abstract": {
        "elements": "non-representational forms, shapes, colors, textures",
        "composition": "balance, rhythm, visual tension, color relationships"
    },
    "religious_painting": {
        "elements": "sacred figures, biblical scenes, halos, divine light",
        "composition": "hierarchical arrangement, symbolic gestures, devotional focus"
    },
    "genre_painting": {
        "elements": "everyday life scenes, common people, domestic activities",
        "composition": "narrative moment, naturalistic setting, social context"
    },
    "history_painting": {
        "elements": "historical events, heroic figures, dramatic moments",
        "composition": "grand scale, theatrical arrangement, narrative clarity"
    },
    "cityscape": {
        "elements": "urban architecture, streets, buildings, city life",
        "composition": "linear perspective, architectural details, urban atmosphere"
    },
    "marina": {
        "elements": "sea, ships, coastal scenes, water reflections",
        "composition": "horizontal emphasis, sky-water relationship, maritime activity"
    },
    "nude_painting": {
        "elements": "human form, anatomical beauty, classical poses",
        "composition": "figure emphasis, careful lighting, idealized proportions"
    },
    "flower_painting": {
        "elements": "floral arrangements, botanical detail, vases, garden scenes",
        "composition": "color harmony, natural arrangements, delicate textures"
    },
    "animal_painting": {
        "elements": "wildlife, domestic animals, natural behavior, fur textures",
        "composition": "animal as protagonist, habitat context, movement capture"
    },
}


def get_style_details(style_name: str) -> dict:
    """Get detailed style information for prompt enhancement."""
    if not style_name:
        return {}
    key = style_name.lower().replace(" ", "_").replace("-", "_")
    return STYLE_DETAILS.get(key, {})


def get_genre_details(genre_name: str) -> dict:
    """Get detailed genre information for prompt enhancement."""
    if not genre_name:
        return {}
    key = genre_name.lower().replace(" ", "_").replace("-", "_")
    return GENRE_DETAILS.get(key, {})


def build_image_generation_prompt(
    artist_name: str,
    style_name: str = None,
    genre_name: str = None,
    user_details: str = None
) -> str:
    """Build prompt for LLM to generate a Stable Diffusion prompt.
    
    Args:
        artist_name: Name of the artist whose style to emulate
        style_name: Optional artistic style (e.g., "Impressionism")
        genre_name: Optional genre (e.g., "landscape", "portrait")
        user_details: Optional user-provided scene description (may be in Russian)
        
    Returns:
        Prompt for the LLM to generate an SD prompt
    """
    # Get detailed style and genre information
    style_info = get_style_details(style_name) if style_name else {}
    genre_info = get_genre_details(genre_name) if genre_name else {}
    
    # Build compact context
    style_context = f", {style_name} style" if style_name else ""
    genre_context = genre_name if genre_name else "artwork"
    
    # Build technique hints
    techniques = style_info.get('techniques', '') if style_info else ''
    colors = style_info.get('colors', '') if style_info else ''
    mood = style_info.get('mood', '') if style_info else ''
    
    if user_details:
        # User provided their idea - incorporate it
        return f"""Create SD prompt for: "{user_details}" in style of {artist_name}{style_context}.
Use: {techniques}. Colors: {colors}. Mood: {mood}.
Add quality tags: masterpiece, highly detailed, 8k."""
    
    # No user details - generate a scene
    elements = genre_info.get('elements', 'artistic scene') if genre_info else 'artistic scene'
    return f"""Create SD prompt for {genre_context} in style of {artist_name}{style_context}.
Include: {elements}. Techniques: {techniques}. Colors: {colors}. Mood: {mood}.
Add quality tags: masterpiece, highly detailed, 8k."""


# Default negative prompt for SD generation
SD_NEGATIVE_PROMPT = "text, watermark, signature, blurry, low quality, deformed, ugly, bad anatomy, disfigured"


def build_sd_style_prompt(
    base_prompt: str,
    artist_name: str,
    style_name: str = None
) -> str:
    """Enhance a base prompt with style modifiers for SD.
    
    This is used as fallback when LLM is not available.
    
    Args:
        base_prompt: The base scene description
        artist_name: Artist name to reference
        style_name: Optional style name
        
    Returns:
        Enhanced SD prompt with style modifiers
    """
    style_suffix = f", {style_name} style" if style_name else ""
    
    return f"{base_prompt}, in the style of {artist_name}{style_suffix}, masterpiece, high quality, detailed"
