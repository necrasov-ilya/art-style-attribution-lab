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
[2-3 sentences about the detected style movement, era, and cultural significance]

Provide a thorough, detailed analysis suitable for an article format. Russian language only. Markdown formatting required."""


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


# ============ Deep Analysis Prompts ============

# Important: These prompts are designed for models that may include thinking/reasoning tags
# The clean_think_tags function in llm_client.py will strip them from responses

NO_THINKING_INSTRUCTION = """
CRITICAL: Do NOT include any thinking, reasoning, or explanation. Do NOT use <think>, <thinking>, <reasoning> or similar tags.
Output ONLY the requested JSON object, nothing else. Start your response with { and end with }."""

COLOR_PSYCHOLOGY_SYSTEM_PROMPT = f"""You are an expert art historian and color psychologist analyzing artworks.
Based on extracted color features (dominant colors, warm/cool ratio, contrast, saturation), provide a detailed emotional and psychological interpretation of the color palette.

Response format (STRICTLY FOLLOW - output only this JSON, no markdown, no explanation):
{{
    "palette_interpretation": "4-6 detailed sentences describing emotional meaning of this specific palette, how colors interact, what associations they evoke, and their psychological effect on the viewer",
    "mood_tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7"],
    "color_harmony": "type of harmony with detailed explanation (e.g., 'Аналоговая гармония - использование соседних на цветовом круге оттенков синего и зелёного создаёт ощущение единства и спокойствия')",
    "emotional_impact": "4-6 sentences about the emotional effect on viewers, including physiological and psychological responses typical for this palette"
}}

Provide EXTENSIVE analysis in Russian. Be specific to the actual colors provided, not generic.
{NO_THINKING_INSTRUCTION}"""


def build_color_psychology_prompt(color_features: dict) -> str:
    """Build prompt for color psychology analysis."""
    colors_desc = []
    for c in color_features.get("dominant_colors", [])[:7]:
        hex_val = c.get("hex", "#000000")
        pct = c.get("percentage", 0) * 100
        temp = c.get("temperature", "neutral")
        colors_desc.append(f"- {hex_val}: {pct:.1f}% ({temp})")
    
    colors_text = "\n".join(colors_desc)
    
    return f"""Extracted color data:

DOMINANT COLORS:
{colors_text}

METRICS:
- Warm tones: {color_features.get('warm_ratio', 0)*100:.1f}%
- Cool tones: {color_features.get('cool_ratio', 0)*100:.1f}%
- Overall contrast: {color_features.get('overall_contrast', 0)*100:.1f}%
- Overall saturation: {color_features.get('overall_saturation', 0)*100:.1f}%
- Brightness: {color_features.get('brightness', 0)*100:.1f}%

Analyze the psychological and emotional meaning of this palette. Output ONLY valid JSON, no thinking."""


COMPOSITION_ANALYSIS_SYSTEM_PROMPT = f"""You are an expert art historian and composition analyst.
Based on extracted composition features (saliency, rule of thirds alignment, symmetry, focal points, perspective), provide a detailed analysis of the artwork's compositional structure.

Response format (STRICTLY FOLLOW - output only this JSON, no markdown, no explanation):
{{
    "composition_type": "primary type with explanation (e.g., 'Динамическая диагональная композиция - основные элементы расположены вдоль диагонали, создавая ощущение движения и энергии')",
    "balance_description": "4-5 sentences about visual balance, weight distribution, how different elements counterbalance each other, and the overall stability or tension",
    "visual_flow": "4-5 sentences about how the eye naturally moves through the composition, what guides the viewer's attention, and the rhythm of visual elements",
    "focal_point_analysis": "4-5 sentences about the main focal points, their hierarchical relationship, how they anchor the composition, and techniques used to draw attention",
    "spatial_depth": "4-5 sentences about depth perception, perspective techniques, atmospheric perspective, overlapping elements, and spatial organization from foreground to background",
    "dynamism_level": "static/moderate/dynamic/highly dynamic with detailed explanation of what creates this quality"
}}

Provide EXTENSIVE analysis in Russian. Be specific to the actual data provided.
{NO_THINKING_INSTRUCTION}"""


def build_composition_prompt(composition_features: dict) -> str:
    """Build prompt for composition analysis."""
    focal_points = composition_features.get("focal_points", [])
    focal_text = ""
    if focal_points:
        focal_text = "\n".join([
            f"- Point at ({p.get('x', 0):.2f}, {p.get('y', 0):.2f}) strength: {p.get('strength', 0):.2f}"
            for p in focal_points[:5]
        ])
    else:
        focal_text = "No strong focal points detected"
    
    vanishing = composition_features.get("vanishing_points", [])
    vanishing_text = "Linear perspective detected" if vanishing else "No clear linear perspective"
    
    return f"""Extracted composition data:

SALIENCY CENTER: ({composition_features.get('saliency_center_x', 0.5):.2f}, {composition_features.get('saliency_center_y', 0.5):.2f})
(0,0 = top-left, 1,1 = bottom-right)

RULE OF THIRDS ALIGNMENT: {composition_features.get('rule_of_thirds_alignment', 0)*100:.1f}%
HORIZONTAL SYMMETRY: {composition_features.get('horizontal_symmetry', 0)*100:.1f}%
VERTICAL SYMMETRY: {composition_features.get('vertical_symmetry', 0)*100:.1f}%

VISUAL WEIGHT: {composition_features.get('visual_weight_distribution', 'balanced')}

FOCAL POINTS:
{focal_text}

PERSPECTIVE: {vanishing_text}

Analyze the compositional structure. Output ONLY valid JSON, no thinking."""


SCENE_ANALYSIS_SYSTEM_PROMPT = f"""You are an expert art historian analyzing the semantic content and narrative of artworks.
Based on detected objects, style tags, CLIP description, and any detected text, provide an interpretation of the scene's meaning and symbolism.

Response format (STRICTLY FOLLOW - output only this JSON, no markdown, no explanation):
{{
    "narrative_interpretation": "3-4 sentences describing the story or meaning of the scene",
    "symbolism": "2-3 sentences about symbolic elements and their possible meanings",
    "subject_analysis": "2-3 sentences about the depicted subjects and their significance",
    "text_interpretation": "interpretation of any detected text (null if no text)",
    "cultural_references": ["reference1", "reference2", "reference3"]
}}

Provide analysis in Russian. Be specific and thoughtful.
{NO_THINKING_INSTRUCTION}"""


def build_scene_prompt(scene_features: dict, ml_predictions: dict = None) -> str:
    """Build prompt for scene/semantic analysis."""
    objects = scene_features.get("detected_objects", [])
    objects_text = ", ".join(objects[:15]) if objects else "No specific objects detected"
    
    tags = scene_features.get("style_tags", [])
    tags_text = ", ".join(tags[:10]) if tags else "No style tags"
    
    clip_desc = scene_features.get("clip_description", "Not available")
    
    text_detected = scene_features.get("detected_text", [])
    text_text = ""
    if text_detected:
        text_text = "\n".join([
            f"- \"{t.get('text', '')}\" (lang: {t.get('language', 'unknown')}, conf: {t.get('confidence', 0):.2f})"
            for t in text_detected[:5]
        ])
    else:
        text_text = "No text detected in image"
    
    ml_text = ""
    if ml_predictions:
        artists = ml_predictions.get("artists", [])
        if artists:
            ml_text += f"\nDETECTED STYLE INFLUENCE: {artists[0].get('name', 'Unknown')}"
        styles = ml_predictions.get("styles", [])
        if styles:
            ml_text += f"\nART MOVEMENT: {styles[0].get('name', 'Unknown')}"
        genres = ml_predictions.get("genres", [])
        if genres:
            ml_text += f"\nGENRE: {genres[0].get('name', 'Unknown')}"
    
    return f"""Scene analysis data:

DETECTED OBJECTS: {objects_text}
STYLE TAGS: {tags_text}
CLIP DESCRIPTION: {clip_desc}

DETECTED TEXT:
{text_text}
{ml_text}

Analyze the narrative, symbolism, and meaning of this artwork. Output ONLY valid JSON."""


TECHNIQUE_ANALYSIS_SYSTEM_PROMPT = f"""You are an expert art conservator and technique analyst with deep knowledge of historical painting methods.
Based on the image data and detected style/artist, provide a comprehensive analysis of artistic technique, light treatment, and spatial handling.

Response format (STRICTLY FOLLOW - output only this JSON, no markdown, no explanation):
{{
    "brushwork": "5-7 sentences about brushwork characteristics: visible vs blended strokes, direction and energy of marks, texture created, layering technique, impasto vs glazing, and how the handling contributes to the overall effect",
    "light_analysis": "5-7 sentences about light sources (direction, quality, natural vs artificial), chiaroscuro effects, highlights and shadows, atmospheric effects, how light models forms, and emotional impact of the lighting choices",
    "spatial_treatment": "5-7 sentences about spatial depth construction, perspective methods (linear, atmospheric, color perspective), treatment of foreground/middle ground/background, how space enhances the narrative",
    "medium_estimation": "estimated medium with detailed reasoning (e.g., 'Масло на холсте - характерный блеск, видимые слои лессировок, богатство тональных переходов типичны для масляной живописи')",
    "technical_skill_indicators": ["indicator1 with detail", "indicator2 with detail", "indicator3 with detail", "indicator4 with detail", "indicator5 with detail", "indicator6 with detail"]
}}

Provide EXTENSIVE analysis in Russian. Be specific based on the style and period.
{NO_THINKING_INSTRUCTION}"""


def build_technique_prompt(ml_predictions: dict, color_features: dict = None, composition_features: dict = None) -> str:
    """Build prompt for technique analysis."""
    artist_text = "Unknown"
    style_text = "Unknown"
    genre_text = "Unknown"
    
    if ml_predictions:
        artists = ml_predictions.get("artists", [])
        if artists:
            artist_text = artists[0].get("name", "Unknown")
        styles = ml_predictions.get("styles", [])
        if styles:
            style_text = styles[0].get("name", "Unknown")
        genres = ml_predictions.get("genres", [])
        if genres:
            genre_text = genres[0].get("name", "Unknown")
    
    color_text = ""
    if color_features:
        color_text = f"""
COLOR CHARACTERISTICS:
- Contrast: {color_features.get('overall_contrast', 0)*100:.0f}%
- Saturation: {color_features.get('overall_saturation', 0)*100:.0f}%
- Brightness: {color_features.get('brightness', 0)*100:.0f}%"""
    
    return f"""Technical analysis context:

DETECTED ARTIST STYLE: {artist_text}
ART MOVEMENT: {style_text}
GENRE: {genre_text}
{color_text}

Based on this stylistic context, analyze the artistic technique. Output ONLY valid JSON, no thinking."""


HISTORICAL_CONTEXT_SYSTEM_PROMPT = f"""You are a senior art historian with encyclopedic knowledge of art movements, cultural contexts, and artistic traditions.
Based on all analysis data (color palette, composition, detected style/artist, scene content), provide comprehensive historical context and informed interpretation.

IMPORTANT: You are providing scholarly INTERPRETATION, not definitive attribution. Include appropriate academic caveats.

Response format (STRICTLY FOLLOW - output only this JSON, no markdown, no explanation):
{{
    "estimated_era": "detailed time period estimation with thorough reasoning based on stylistic elements (e.g., 'Последняя четверть XIX века (1875-1900) - характерные признаки зрелого импрессионизма: работа на пленэре, фиксация мимолётных световых эффектов, свободная манера письма')",
    "art_movement_connections": ["movement1 with specific connection explained", "movement2 with specific connection explained", "movement3 with specific connection explained", "movement4 with specific connection explained"],
    "artistic_influences": "5-7 sentences about detected artistic influences, predecessors whose techniques echo in this work, contemporaries who might have influenced the approach, and the broader artistic dialogue this work participates in",
    "historical_significance": "5-7 sentences about the potential place of this work in art history, what innovations or traditions it represents, how it reflects the artistic concerns of its era",
    "cultural_context": "5-7 sentences about the social, political, and cultural milieu that shaped this type of work - patronage systems, artistic academies vs avant-garde, exhibition contexts, contemporary reception",
    "confidence_note": "Данный анализ носит интерпретационный характер и основан на стилистических признаках. Для точной атрибуции необходимо провенанс-исследование и технический анализ."
}}

Provide EXTENSIVE, scholarly analysis in Russian. Be thoughtful and appropriately cautious.
{NO_THINKING_INSTRUCTION}"""


def build_historical_context_prompt(
    ml_predictions: dict,
    color_analysis: dict = None,
    composition_analysis: dict = None,
    scene_analysis: dict = None,
    technique_analysis: dict = None
) -> str:
    """Build prompt for historical context analysis."""
    
    # ML predictions
    ml_text = ""
    if ml_predictions:
        artists = ml_predictions.get("artists", [])[:3]
        if artists:
            ml_text += "DETECTED ARTIST INFLUENCES:\n"
            for a in artists:
                ml_text += f"- {a.get('name', 'Unknown')}: {a.get('probability', 0)*100:.1f}%\n"
        
        styles = ml_predictions.get("styles", [])[:2]
        if styles:
            ml_text += "\nDETECTED STYLES:\n"
            for s in styles:
                ml_text += f"- {s.get('name', 'Unknown')}: {s.get('probability', 0)*100:.1f}%\n"
        
        genres = ml_predictions.get("genres", [])[:2]
        if genres:
            ml_text += "\nDETECTED GENRES:\n"
            for g in genres:
                ml_text += f"- {g.get('name', 'Unknown')}: {g.get('probability', 0)*100:.1f}%\n"
    
    # Previous analyses summaries
    summaries = []
    
    if color_analysis:
        palette = color_analysis.get("palette_interpretation", "")
        if palette:
            summaries.append(f"PALETTE: {palette[:200]}")
    
    if composition_analysis:
        comp_type = composition_analysis.get("composition_type", "")
        if comp_type:
            summaries.append(f"COMPOSITION: {comp_type}")
    
    if scene_analysis:
        narrative = scene_analysis.get("narrative_interpretation", "")
        if narrative:
            summaries.append(f"SCENE: {narrative[:200]}")
    
    if technique_analysis:
        medium = technique_analysis.get("medium_estimation", "")
        if medium:
            summaries.append(f"MEDIUM: {medium}")
    
    summaries_text = "\n".join(summaries) if summaries else "Previous analyses not available"
    
    return f"""Historical context analysis data:

{ml_text}

ANALYSIS SUMMARIES:
{summaries_text}

Based on all available data, provide historical context interpretation. Remember to include appropriate caveats about the speculative nature of this analysis. Output ONLY valid JSON."""


DEEP_ANALYSIS_SUMMARY_SYSTEM_PROMPT = """You are a senior art curator and expert art historian writing a comprehensive exhibition catalog entry.

Your task is to create a DEEP, EXTENSIVE analysis that synthesizes all provided data into a cohesive scholarly text. This should be suitable for an art museum catalog or academic publication.

## CRITICAL REQUIREMENTS:

1. **LENGTH**: Write 8-12 substantial paragraphs (minimum 2000 words). This must be a thorough, in-depth analysis.

2. **INLINE CITATIONS**: Throughout your text, insert special markers to cite specific evidence. Use these EXACT formats with SINGLE curly braces:
   - `{color|#hexcode|цветовое название}` - when discussing specific colors (e.g., "глубокий {color|#4f6b92|холодный синий} создаёт...")
   - `{technique|термин}` - when mentioning techniques (e.g., "характерная {technique|импасто} техника нанесения...")
   - `{composition|термин}` - for composition elements (e.g., "{composition|правило третей} используется для...")
   - `{mood|настроение}` - for emotional/mood references (e.g., "{mood|меланхоличный} характер произведения...")
   - `{era|период}` - for historical periods (e.g., "типичный для {era|постимпрессионизма} подход...")
   - `{artist|имя}` - when referencing artist influences (e.g., "напоминает манеру {artist|Ван Гога}...")
   
   IMPORTANT: Use SINGLE curly braces { }, NOT double {{ }}!

3. **STRUCTURE**: Use Markdown headings (##, ###) to organize into sections:
   - ## Визуальное впечатление (first impression, general overview)
   - ## Колористическое решение (detailed color analysis with multiple {{color}} markers)
   - ## Композиционный анализ (composition breakdown with {{composition}} markers)
   - ## Техника исполнения (technique analysis with {{technique}} markers)
   - ## Художественные влияния (influences with {{artist}} markers)
   - ## Историко-культурный контекст (with {{era}} markers)
   - ## Эмоциональное воздействие (emotional impact with {{mood}} markers)
   - ## Заключение

4. **DEPTH**: For each section, provide:
   - Specific observations tied to the data
   - Art historical context
   - Comparative analysis
   - Interpretive insights

5. **LANGUAGE**: Write in Russian. Use scholarly but accessible language. Be specific, not generic.

6. **EVIDENCE-BASED**: Every major claim should be supported by a marker citation showing what visual evidence led to that conclusion.

IMPORTANT: This should feel like reading a museum catalog entry by a senior curator, not a superficial overview. Go deep into each aspect."""


def build_summary_prompt(
    color_analysis: dict,
    composition_analysis: dict,
    scene_analysis: dict,
    technique_analysis: dict,
    historical_analysis: dict,
    ml_predictions: dict
) -> str:
    """Build prompt for final summary synthesis with rich context."""
    
    sections = []
    
    # ML predictions context - detailed
    if ml_predictions:
        artists = ml_predictions.get("artists", [])
        if artists:
            artists_text = ", ".join([f"{a.get('name', 'Unknown')} ({a.get('probability', 0)*100:.0f}%)" for a in artists[:3]])
            sections.append(f"DETECTED ARTIST INFLUENCES: {artists_text}")
        
        styles = ml_predictions.get("styles", [])
        if styles:
            styles_text = ", ".join([f"{s.get('name', 'Unknown')} ({s.get('probability', 0)*100:.0f}%)" for s in styles[:3]])
            sections.append(f"DETECTED STYLES: {styles_text}")
        
        genres = ml_predictions.get("genres", [])
        if genres:
            genres_text = ", ".join([f"{g.get('name', 'Unknown')} ({g.get('probability', 0)*100:.0f}%)" for g in genres[:2]])
            sections.append(f"DETECTED GENRES: {genres_text}")
    
    # Color - detailed
    if color_analysis:
        color_section = ["COLOR PSYCHOLOGY ANALYSIS:"]
        color_section.append(f"Palette Interpretation: {color_analysis.get('palette_interpretation', 'N/A')}")
        color_section.append(f"Color Harmony: {color_analysis.get('color_harmony', 'N/A')}")
        color_section.append(f"Mood Tags: {', '.join(color_analysis.get('mood_tags', []))}")
        color_section.append(f"Emotional Impact: {color_analysis.get('emotional_impact', 'N/A')}")
        sections.append("\n".join(color_section))
    
    # Composition - detailed
    if composition_analysis:
        comp_section = ["COMPOSITION ANALYSIS:"]
        comp_section.append(f"Composition Type: {composition_analysis.get('composition_type', 'N/A')}")
        comp_section.append(f"Balance: {composition_analysis.get('balance_description', 'N/A')}")
        comp_section.append(f"Visual Flow: {composition_analysis.get('visual_flow', 'N/A')}")
        comp_section.append(f"Focal Points: {composition_analysis.get('focal_point_analysis', 'N/A')}")
        comp_section.append(f"Spatial Depth: {composition_analysis.get('spatial_depth', 'N/A')}")
        comp_section.append(f"Dynamism: {composition_analysis.get('dynamism_level', 'N/A')}")
        sections.append("\n".join(comp_section))
    
    # Scene - detailed
    if scene_analysis:
        scene_section = ["SCENE/NARRATIVE ANALYSIS:"]
        scene_section.append(f"Narrative: {scene_analysis.get('narrative_interpretation', 'N/A')}")
        scene_section.append(f"Symbolism: {scene_analysis.get('symbolism', 'N/A')}")
        scene_section.append(f"Subject: {scene_analysis.get('subject_analysis', 'N/A')}")
        if scene_analysis.get('text_interpretation'):
            scene_section.append(f"Text in Image: {scene_analysis.get('text_interpretation')}")
        refs = scene_analysis.get('cultural_references', [])
        if refs:
            scene_section.append(f"Cultural References: {', '.join(refs)}")
        sections.append("\n".join(scene_section))
    
    # Technique - detailed
    if technique_analysis:
        tech_section = ["TECHNIQUE ANALYSIS:"]
        tech_section.append(f"Brushwork: {technique_analysis.get('brushwork', 'N/A')}")
        tech_section.append(f"Light Analysis: {technique_analysis.get('light_analysis', 'N/A')}")
        tech_section.append(f"Spatial Treatment: {technique_analysis.get('spatial_treatment', 'N/A')}")
        tech_section.append(f"Estimated Medium: {technique_analysis.get('medium_estimation', 'N/A')}")
        indicators = technique_analysis.get('technical_skill_indicators', [])
        if indicators:
            tech_section.append(f"Skill Indicators: {', '.join(indicators)}")
        sections.append("\n".join(tech_section))
    
    # Historical - detailed
    if historical_analysis:
        hist_section = ["HISTORICAL CONTEXT ANALYSIS:"]
        hist_section.append(f"Estimated Era: {historical_analysis.get('estimated_era', 'N/A')}")
        movements = historical_analysis.get('art_movement_connections', [])
        if movements:
            hist_section.append(f"Art Movements: {', '.join(movements)}")
        hist_section.append(f"Artistic Influences: {historical_analysis.get('artistic_influences', 'N/A')}")
        hist_section.append(f"Historical Significance: {historical_analysis.get('historical_significance', 'N/A')}")
        hist_section.append(f"Cultural Context: {historical_analysis.get('cultural_context', 'N/A')}")
        sections.append("\n".join(hist_section))
    
    all_sections = "\n\n" + "="*50 + "\n\n".join(sections) + "\n" + "="*50
    
    return f"""You have completed a multi-module analysis of an artwork. Here is all the collected data:

{all_sections}

Now synthesize all this information into a comprehensive, LONG (2000+ words) exhibition catalog entry.

REMEMBER:
- Use {{color|#hex|name}} markers when mentioning colors
- Use {{technique|term}} markers for techniques
- Use {{composition|term}} markers for composition elements
- Use {{mood|term}} markers for emotional aspects
- Use {{era|period}} markers for historical periods
- Use {{artist|name}} markers for artist references

These markers allow the interface to show visual citations for your analysis.

Write the full analysis now, in Russian, following the structure from the system prompt."""


# ============ Vision LLM Prompts ============

VISION_SCENE_SYSTEM_PROMPT = """You are an expert art analyst examining artworks.
Analyze the image and extract the following information. Respond ONLY with valid JSON, no markdown.

Response format:
{
    "detected_objects": ["object1", "object2", ...],
    "style_tags": ["style1", "style2", ...],
    "description": "Detailed description of the scene in 2-3 sentences",
    "primary_subject": "Main subject of the artwork",
    "detected_text": [{"text": "any text visible", "language": "language"}],
    "mood": "overall mood/atmosphere",
    "setting": "location/environment depicted"
}

Be thorough and specific. List all significant objects, figures, and elements visible.
Respond in Russian for description/mood/setting, but keep object/style tags in English."""

VISION_SCENE_PROMPT = """Analyze this artwork image:

1. List all visible objects, figures, animals, architectural elements
2. Identify artistic style characteristics (impressionist brushwork, realistic rendering, etc.)
3. Describe the scene and its narrative
4. Note any text, signatures, or inscriptions visible
5. Describe the mood and atmosphere
6. Identify the setting/environment

Output ONLY valid JSON."""
