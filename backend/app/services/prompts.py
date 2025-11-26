"""Prompt templates for LLM-based art analysis and SD prompt generation.

This module contains all prompt templates used by the LLM service.
The project uses a WikiArt-trained MobileNetV2 model that classifies:
- Artists (129 artists from WikiArt dataset)
- Genres (portrait, landscape, still_life, etc.)
- Styles (Impressionism, Baroque, Cubism, etc.)

LLM is used for two purposes:
1. Generate human-readable analysis of ML predictions (in Russian)
2. Convert ML predictions into Stable Diffusion prompts for image generation
"""

ANALYSIS_SYSTEM_PROMPT = """You are an expert art historian providing analysis of artwork classification results. 
A neural network has analyzed an uploaded image and identified similar artists, genres, and styles from the WikiArt dataset.
Your task is to explain these results in Russian using Markdown formatting.

Response format (strictly follow):
## 🎨 Художественный анализ
[2-3 sentences describing the main stylistic characteristics detected]

### Ключевые характеристики
- **Техника**: [brushwork, composition methods]
- **Палитра**: [color characteristics]
- **Композиция**: [compositional features]

### Влияние мастеров
**[Artist 1]** (XX%): [what specific traits connect to this artist]
**[Artist 2]** (XX%): [what specific traits connect to this artist]
**[Artist 3]** (XX%): [what specific traits connect to this artist]

### Историко-художественный контекст
[1-2 sentences about the detected style movement and era]

Maximum 250 words. Russian language only. Markdown formatting required."""


def build_analysis_prompt(artists: list, genres: list, styles: list) -> str:
    """Build user prompt with ML classification results."""
    artists_text = "\n".join([
        f"- {a['name']}: {a['probability']:.1%} confidence"
        for a in artists[:3]
    ]) if artists else "No artists detected"
    
    genres_text = ", ".join([
        f"{g['name']} ({g['probability']:.1%})"
        for g in genres[:2]
    ]) if genres else "Not detected"
    
    styles_text = ", ".join([
        f"{s['name']} ({s['probability']:.1%})"
        for s in styles[:2]
    ]) if styles else "Not detected"
    
    return f"""ML Classification Results:

DETECTED ARTISTS:
{artists_text}

DETECTED GENRE: {genres_text}
DETECTED STYLE: {styles_text}

Provide analysis in Russian following the format from system prompt."""


def format_prediction_for_prompt(prediction: dict) -> dict:
    """Convert ML prediction to prompt-friendly format."""
    name = prediction.get("name") or prediction.get("artist_slug", "Unknown")
    name = name.replace("-", " ").replace("_", " ").title()
    return {"name": name, "probability": prediction.get("probability", 0.0)}


SD_PROMPT_SYSTEM = """You are a Stable Diffusion prompt engineer. Your task is to create image generation prompts that accurately reproduce the visual style of specific artists from the WikiArt dataset.

Given an artist name, art movement, and genre, create a detailed prompt that captures:
1. The artist's characteristic brushwork and technique
2. Their typical color palette and lighting
3. Compositional style and subject matter
4. Quality and style modifiers for best results

Output format: A single comma-separated prompt in English, 80-120 words.
Include quality tags: masterpiece, highly detailed, museum quality, 8k

IMPORTANT: Output ONLY the prompt text. No explanations, no thinking, no tags."""


SD_PROMPT_WITH_IDEA_SYSTEM = """You are a Stable Diffusion prompt engineer. Your task is to transform a user's scene idea into a prompt that renders it in the style of a specific WikiArt artist.

Given an artist name, style, and user's scene description (may be in Russian), create a prompt that:
1. Preserves the user's concept and translates it to English if needed
2. Applies the artist's characteristic technique and visual style
3. Uses appropriate color palette and composition for that artist
4. Adds quality modifiers for best results

Output format: A single comma-separated prompt in English, 80-120 words.
Include quality tags: masterpiece, highly detailed, museum quality, 8k

IMPORTANT: Output ONLY the prompt text. No explanations, no thinking, no tags."""


ARTIST_STYLES = {
    "vincent-van-gogh": "swirling brushstrokes, thick impasto, vibrant yellows and blues, emotional intensity, expressive texture, Post-Impressionist",
    "claude-monet": "soft dappled light, broken color, atmospheric effects, water reflections, Impressionist brushwork, natural scenes",
    "pablo-picasso": "geometric fragmentation, multiple perspectives, bold outlines, Cubist deconstruction, analytical forms",
    "rembrandt": "dramatic chiaroscuro, warm golden tones, psychological depth, masterful portraiture, Dutch Golden Age",
    "salvador-dali": "hyperrealistic surrealism, melting forms, dreamlike imagery, precise detail, symbolic elements",
    "gustav-klimt": "gold leaf decorations, ornamental patterns, sensual figures, Art Nouveau elegance, Byzantine influence",
    "edvard-munch": "emotional distortion, anxious atmosphere, bold colors, Expressionist intensity, psychological themes",
    "henri-matisse": "pure vivid colors, simplified forms, decorative patterns, Fauvist boldness, joyful expression",
    "leonardo-da-vinci": "sfumato technique, perfect anatomy, Renaissance mastery, subtle gradations, classical beauty",
    "michelangelo": "powerful anatomy, dynamic poses, monumental scale, sculptural forms, High Renaissance grandeur",
    "ivan-aivazovsky": "luminous seascapes, dramatic waves, atmospheric light, maritime mastery, Romantic realism",
    "ilya-repin": "Russian Realism, psychological depth, historical drama, masterful technique, narrative power",
    "katsushika-hokusai": "Ukiyo-e woodblock style, bold outlines, flat color areas, Japanese aesthetics, iconic compositions",
    "pierre-auguste-renoir": "soft luminous skin tones, joyful scenes, dappled sunlight, Impressionist warmth, feminine beauty",
    "edgar-degas": "dynamic compositions, ballet dancers, unusual angles, pastel mastery, movement capture",
    "paul-cezanne": "geometric simplification, constructive brushstrokes, modulated color, proto-Cubist forms",
    "paul-gauguin": "bold flat colors, Tahitian scenes, symbolic imagery, primitive style, exotic themes",
    "camille-pissarro": "rural scenes, peasant life, Impressionist atmosphere, gentle colors, pastoral tranquility",
    "francisco-goya": "dark psychological depth, social critique, dramatic contrasts, Spanish Romanticism",
    "el-greco": "elongated figures, mystical lighting, intense spirituality, Mannerist distortion, Byzantine influence",
    "peter-paul-rubens": "voluptuous forms, dynamic movement, rich colors, Baroque grandeur, sensual flesh tones",
    "titian": "rich Venetian color, masterful glazing, sensual beauty, Renaissance magnificence",
    "william-turner": "atmospheric light, sublime nature, romantic seascapes, proto-Impressionist techniques",
    "gustave-courbet": "honest realism, earthy palette, working class subjects, thick impasto",
    "edouard-manet": "bold contrasts, modern life subjects, revolutionary technique, pre-Impressionist",
    "henri-de-toulouse-lautrec": "Parisian nightlife, bold outlines, poster art style, expressive characters",
    "marc-chagall": "dreamlike fantasy, floating figures, vivid colors, Jewish folklore, romantic whimsy",
    "amedeo-modigliani": "elongated faces, almond eyes, elegant simplification, sculptural forms",
    "egon-schiele": "raw expressionism, contorted bodies, intense lines, psychological rawness",
    "georges-seurat": "pointillist dots, scientific color theory, luminous effects, Neo-Impressionist",
}

STYLE_CHARACTERISTICS = {
    "impressionism": "visible brushstrokes, natural light, outdoor scenes, color vibration, momentary effects, plein air painting",
    "post_impressionism": "bold colors, expressive brushwork, emotional depth, geometric structure, personal vision",
    "expressionism": "distorted forms, intense colors, emotional content, psychological drama, subjective reality",
    "baroque": "dramatic lighting, rich detail, dynamic composition, theatrical grandeur, chiaroscuro",
    "high_renaissance": "linear perspective, balanced composition, classical ideals, anatomical precision, harmonious proportions",
    "early_renaissance": "emerging perspective, religious themes, gold backgrounds, symbolic imagery",
    "northern_renaissance": "meticulous detail, oil painting mastery, domestic scenes, symbolic objects",
    "mannerism_late_renaissance": "elongated forms, unusual colors, complex poses, sophisticated elegance",
    "cubism": "fragmented forms, multiple viewpoints, geometric shapes, analytical deconstruction, flattened space",
    "analytical_cubism": "monochromatic palette, fragmented planes, overlapping forms",
    "synthetic_cubism": "collage elements, brighter colors, decorative patterns, simplified forms",
    "surrealism": "dreamlike imagery, unexpected juxtapositions, subconscious themes, precise rendering of impossible scenes",
    "romanticism": "dramatic nature, emotional intensity, sublime landscapes, heroic themes, rich colors",
    "realism": "accurate observation, everyday subjects, natural lighting, honest depiction, social themes",
    "contemporary_realism": "photographic accuracy, modern subjects, technical precision",
    "new_realism": "everyday objects, consumer culture, assemblage techniques",
    "art_nouveau": "flowing organic lines, decorative elegance, natural forms, ornamental beauty, stylized patterns",
    "symbolism": "mystical themes, allegorical content, dreamlike atmosphere, poetic imagery, spiritual depth",
    "fauvism": "wild color, simplified forms, bold brushwork, non-naturalistic palette, joyful expression",
    "pointillism": "small color dots, optical mixing, luminous effect, scientific approach, vibrant surface",
    "ukiyo_e": "flat colors, bold outlines, Japanese aesthetics, elegant compositions, woodblock print style",
    "abstract_expressionism": "gestural marks, emotional intensity, large scale, spontaneous expression, color fields",
    "action_painting": "dynamic gestures, drip techniques, physical energy, spontaneous creation",
    "color_field_painting": "large color areas, meditative quality, subtle variations, flat application",
    "pop_art": "bold colors, commercial imagery, ironic commentary, graphic style, mass culture references",
    "minimalism": "geometric forms, industrial materials, reduced elements, pure shapes",
    "naive_art_primitivism": "childlike simplicity, bright colors, flat perspective, folk art influence",
    "rococo": "pastel colors, playful themes, ornate decoration, aristocratic elegance",
}

GENRE_ELEMENTS = {
    "portrait": "human face as focus, expressive features, psychological depth, careful lighting on subject",
    "landscape": "natural scenery, atmospheric perspective, sky and terrain, seasonal mood, depth and space",
    "still_life": "arranged objects, symbolic elements, surface textures, careful composition, intimate scale",
    "cityscape": "urban architecture, street scenes, city atmosphere, linear perspective, human activity",
    "religious_painting": "sacred figures, divine light, spiritual symbolism, devotional composition",
    "genre_painting": "everyday life scenes, narrative moment, common people, domestic settings",
    "abstract_painting": "non-representational forms, color relationships, visual rhythm, pure composition",
    "nude_painting": "human form, classical poses, anatomical beauty, artistic tradition",
    "illustration": "narrative clarity, decorative elements, graphic quality, storytelling",
    "sketch_and_study": "loose lines, exploratory marks, preparatory work, artistic process",
}


def build_sd_generation_prompt(artist_name: str, style_name: str = None, genre_name: str = None, user_idea: str = None) -> str:
    """Build the user prompt for SD prompt generation."""
    artist_key = artist_name.lower().replace(" ", "-")
    artist_style = ARTIST_STYLES.get(artist_key, f"distinctive artistic style of {artist_name}")
    
    style_key = style_name.lower().replace(" ", "_") if style_name else None
    style_desc = STYLE_CHARACTERISTICS.get(style_key, "") if style_key else ""
    
    genre_key = genre_name.lower().replace(" ", "_") if genre_name else None
    genre_desc = GENRE_ELEMENTS.get(genre_key, "") if genre_key else ""
    
    context_parts = [f"Artist: {artist_name}", f"Visual characteristics: {artist_style}"]
    
    if style_name and style_desc:
        context_parts.append(f"Art movement ({style_name}): {style_desc}")
    
    if genre_name and genre_desc:
        context_parts.append(f"Genre ({genre_name}): {genre_desc}")
    
    context = "\n".join(context_parts)
    
    if user_idea:
        return f"""{context}

User's scene idea: {user_idea}

Create a Stable Diffusion prompt that renders this scene in {artist_name}'s authentic style."""
    
    return f"""{context}

Create a Stable Diffusion prompt for a {genre_name or 'painting'} that authentically captures {artist_name}'s style."""


def build_fallback_sd_prompt(base_prompt: str, artist_name: str, style_name: str = None) -> str:
    """Build SD prompt without LLM (fallback)."""
    artist_key = artist_name.lower().replace(" ", "-")
    artist_style = ARTIST_STYLES.get(artist_key, f"style of {artist_name}")
    style_suffix = f", {style_name} movement" if style_name else ""
    return f"{base_prompt}, {artist_style}{style_suffix}, masterpiece, highly detailed, museum quality, 8k"


SD_NEGATIVE_PROMPT = "text, watermark, signature, blurry, low quality, deformed, ugly, bad anatomy, disfigured, amateur"
