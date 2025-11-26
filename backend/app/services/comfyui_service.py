"""ComfyUI service - generates images in detected artistic styles.

This module provides the high-level interface for generating artwork thumbnails
using ComfyUI. It uses the LLM to generate creative prompts based on detected styles.
"""
import logging
import uuid
from typing import List, Optional, Dict, Any

from app.core.config import settings
from app.models.schemas import (
    ArtistPrediction,
    GenrePrediction,
    StylePrediction,
    GeneratedThumbnail
)
from app.services.comfyui_client import get_comfyui_client, ComfyUIError
from app.services.llm_client import get_cached_provider, LLMError, clean_think_tags
from app.services.prompts import (
    IMAGE_GEN_SYSTEM_PROMPT,
    IMAGE_GEN_WITH_DETAILS_PROMPT,
    build_image_generation_prompt,
    build_sd_style_prompt,
    SD_NEGATIVE_PROMPT
)

logger = logging.getLogger(__name__)


# Fallback prompts when LLM is not available
FALLBACK_SCENE_PROMPTS = [
    "a serene landscape with mountains and a calm lake at sunset",
    "a portrait of a person in contemplative mood, soft lighting",
    "a still life arrangement with flowers and fruits on a table",
    "an atmospheric city street scene with buildings and figures",
]


async def generate_sd_prompt(
    artist_name: str,
    style_name: Optional[str] = None,
    genre_name: Optional[str] = None,
    user_details: Optional[str] = None
) -> str:
    """Generate a Stable Diffusion prompt using LLM.
    
    Args:
        artist_name: Name of the artist to emulate
        style_name: Optional artistic style
        genre_name: Optional genre
        user_details: Optional user-provided scene details
        
    Returns:
        Generated SD prompt string
    """
    # Check if LLM is available
    if settings.LLM_PROVIDER.lower() == "none":
        # Use fallback prompt
        import random
        base = user_details if user_details else random.choice(FALLBACK_SCENE_PROMPTS)
        return build_sd_style_prompt(base, artist_name, style_name)
    
    try:
        provider = get_cached_provider()
        user_prompt = build_image_generation_prompt(
            artist_name, style_name, genre_name, user_details
        )
        
        # Use different system prompt if user provided details
        system_prompt = IMAGE_GEN_WITH_DETAILS_PROMPT if user_details else IMAGE_GEN_SYSTEM_PROMPT
        
        response = await provider.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=150,
            temperature=0.8
        )
        
        # CRITICAL: Ensure response is clean before using as SD prompt
        # Defense in depth - clean again even though llm_client should have cleaned
        prompt = clean_think_tags(response)
        prompt = prompt.strip().strip('"').strip("'")
        return prompt
        
    except LLMError as e:
        logger.warning(f"LLM prompt generation failed: {e}, using fallback")
        import random
        base = user_details if user_details else random.choice(FALLBACK_SCENE_PROMPTS)
        return build_sd_style_prompt(base, artist_name, style_name)


async def generate_images_with_prompt(
    artist_slug: str,
    style_name: Optional[str] = None,
    genre_name: Optional[str] = None,
    user_details: Optional[str] = None,
    count: int = 4
) -> Dict[str, Any]:
    """
    Generate images in a specific artistic style with optional user details.
    
    This is the main entry point for the /generate endpoint.
    
    Args:
        artist_slug: Artist slug (e.g., "vincent-van-gogh")
        style_name: Optional style name
        genre_name: Optional genre name
        user_details: Optional user-provided scene description
        count: Number of images to generate
        
    Returns:
        Dict with 'prompt' and 'images' keys
    """
    artist_name = artist_slug.replace("-", " ").title()
    style_display = style_name.replace("_", " ").title() if style_name else None
    genre_display = genre_name.replace("_", " ").title() if genre_name else None
    
    # Generate prompt using LLM (incorporating user details)
    sd_prompt = await generate_sd_prompt(artist_name, style_display, genre_display, user_details)
    logger.info(f"Generated SD prompt: {sd_prompt}")
    
    client = get_comfyui_client()
    
    # Check if ComfyUI is available
    if not settings.COMFYUI_ENABLED or not await client.is_available():
        logger.warning("ComfyUI is not available, using placeholder images")
        return {
            "prompt": sd_prompt,
            "images": [
                {"url": f"https://picsum.photos/seed/{uuid.uuid4().hex[:8]}/512/512"}
                for _ in range(count)
            ]
        }
    
    try:
        # Load and prepare workflow
        workflow = client.load_workflow("txt2img_style")
        workflow = client.prepare_workflow(
            workflow=workflow,
            positive_prompt=sd_prompt,
            negative_prompt=SD_NEGATIVE_PROMPT,
            batch_size=count
        )
        
        # Queue and wait for execution
        prompt_id = await client.queue_prompt(workflow)
        logger.info(f"Queued ComfyUI prompt: {prompt_id}")
        
        history = await client.wait_for_completion(prompt_id)
        
        # Extract generated images
        filenames = client.extract_image_filenames(history)
        logger.info(f"Generated {len(filenames)} images")
        
        # Build image URLs
        images = [
            {"url": f"{settings.COMFYUI_BASE_URL}/view?filename={filename}&type=output"}
            for filename in filenames[:count]
        ]
        
        return {
            "prompt": sd_prompt,
            "images": images
        }
        
    except ComfyUIError as e:
        logger.error(f"ComfyUI generation failed: {e}")
        # Return placeholder on error
        return {
            "prompt": sd_prompt,
            "images": [
                {"url": f"https://picsum.photos/seed/{uuid.uuid4().hex[:8]}/512/512"}
                for _ in range(count)
            ]
        }
