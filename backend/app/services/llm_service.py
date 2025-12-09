"""LLM service - generates explanations for art analysis results.

This module provides the high-level interface for generating LLM explanations.
It uses the llm_client for provider abstraction and prompts module for templates.
"""
import json
import logging
from typing import List, Dict, Any, AsyncGenerator

import httpx

from app.models.schemas import (
    ArtistPrediction, 
    GenrePrediction,
    StylePrediction, 
    AnalysisExplanation
)
from app.services.llm_client import (
    get_cached_provider, 
    LLMError, 
    clean_think_tags,
    generate_with_vision
)
from app.services.prompts import (
    ANALYSIS_SYSTEM_PROMPT,
    build_analysis_prompt,
    build_analysis_prompt_with_vision,
    format_prediction_for_prompt,
    VISION_UNKNOWN_ARTIST_SYSTEM_PROMPT,
    VISION_UNKNOWN_ARTIST_PROMPT,
)
from app.core.config import settings

logger = logging.getLogger(__name__)


# ============ Vision Analysis for Unknown Artist ============

async def analyze_unknown_artist_with_vision(image_path: str) -> Dict[str, Any]:
    """
    Use Vision LLM to analyze artwork when ML model returns Unknown Artist.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Dict with analysis results including possible artist identification
    """
    try:
        response = await generate_with_vision(
            image_path=image_path,
            prompt=VISION_UNKNOWN_ARTIST_PROMPT,
            system_prompt=VISION_UNKNOWN_ARTIST_SYSTEM_PROMPT,
            max_tokens=1024,
            temperature=0.3  # Lower temp for more consistent JSON output
        )
        
        # Clean response and parse JSON
        response = clean_think_tags(response).strip()
        
        # Remove markdown code blocks if present
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()
        
        try:
            result = json.loads(response)
            logger.info(f"Vision analysis result: artist={result.get('artist_name')}, confidence={result.get('confidence')}")
            return result
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Vision response as JSON: {e}")
            logger.error(f"Raw response: {response[:500]}")
            # Return a default structure
            return {
                "is_photo": False,
                "artist_name": None,
                "artist_name_ru": "Неизвестный художник",
                "confidence": "none",
                "reasoning": "Не удалось проанализировать изображение",
                "artwork_description": response[:500] if response else "Описание недоступно",
                "style_indicators": [],
                "period_estimate": "Неизвестен"
            }
            
    except Exception as e:
        logger.error(f"Vision analysis failed: {e}")
        return {
            "is_photo": False,
            "artist_name": None,
            "artist_name_ru": "Неизвестный художник", 
            "confidence": "none",
            "reasoning": f"Ошибка анализа: {str(e)}",
            "artwork_description": "Не удалось получить описание",
            "style_indicators": [],
            "period_estimate": "Неизвестен"
        }


# ============ Streaming LLM Generation ============

async def generate_explanation_streaming(
    top_artists: List[ArtistPrediction],
    top_genres: List[GenrePrediction] = None,
    top_styles: List[StylePrediction] = None,
    vision_context: Dict[str, Any] = None
) -> AsyncGenerator[str, None]:
    """
    Generate LLM explanation with real-time streaming (SSE).
    
    Args:
        top_artists: List of artist predictions
        top_genres: List of genre predictions
        top_styles: List of style predictions
        vision_context: Optional Vision LLM analysis for Unknown Artist
        
    Yields:
        Chunks of text as they are generated
    """
    if not top_artists:
        yield "No artists detected in the image."
        return
    
    # Convert predictions to prompt format
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
    
    # Build prompt - add vision context if available
    if vision_context:
        user_prompt = build_analysis_prompt_with_vision(
            artists_data, genres_data, styles_data, vision_context
        )
    else:
        user_prompt = build_analysis_prompt(artists_data, genres_data, styles_data)
    
    # Stream from LLM
    try:
        provider_name = settings.LLM_PROVIDER.lower()
        
        if provider_name == "none":
            # Stub mode - yield stub response
            stub = _build_stub_explanation(top_artists, top_genres, top_styles)
            yield stub.text
            return
        
        async for chunk in _stream_llm_response(
            system_prompt=ANALYSIS_SYSTEM_PROMPT,
            user_prompt=user_prompt
        ):
            yield chunk
            
    except Exception as e:
        logger.error(f"Streaming generation failed: {e}")
        yield f"\n\n[Ошибка генерации: {str(e)}]"


async def _stream_llm_response(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 2048,
    temperature: float = 0.7
) -> AsyncGenerator[str, None]:
    """Stream response from the configured LLM provider."""
    
    provider_name = settings.LLM_PROVIDER.lower()
    
    if provider_name == "openrouter":
        async for chunk in _stream_openrouter(system_prompt, user_prompt, max_tokens, temperature):
            yield chunk
    elif provider_name == "openai":
        async for chunk in _stream_openai(system_prompt, user_prompt, max_tokens, temperature):
            yield chunk
    elif provider_name == "ollama":
        async for chunk in _stream_ollama(system_prompt, user_prompt, max_tokens, temperature):
            yield chunk
    else:
        yield "Streaming не поддерживается для текущего LLM провайдера."


async def _stream_openrouter(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    temperature: float
) -> AsyncGenerator[str, None]:
    """Stream from OpenRouter API."""
    if not settings.OPENROUTER_API_KEY:
        yield "OpenRouter API ключ не настроен."
        return
    
    timeout = httpx.Timeout(settings.LLM_TIMEOUT, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            async with client.stream(
                "POST",
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://art-style-attribution-lab.local",
                    "X-Title": "Art Style Attribution Lab"
                },
                json={
                    "model": settings.OPENROUTER_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "stream": True
                }
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            parsed = json.loads(data)
                            delta = parsed.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                # Stream as-is, cleanup happens on frontend
                                yield content
                        except json.JSONDecodeError:
                            pass
        except Exception as e:
            logger.error(f"OpenRouter streaming error: {e}")
            yield f"\n\n[Ошибка OpenRouter: {str(e)}]"


async def _stream_openai(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    temperature: float
) -> AsyncGenerator[str, None]:
    """Stream from OpenAI API."""
    if not settings.OPENAI_API_KEY:
        yield "OpenAI API ключ не настроен."
        return
    
    timeout = httpx.Timeout(settings.LLM_TIMEOUT, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            async with client.stream(
                "POST",
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": settings.OPENAI_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "stream": True
                }
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            parsed = json.loads(data)
                            delta = parsed.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            pass
        except Exception as e:
            logger.error(f"OpenAI streaming error: {e}")
            yield f"\n\n[Ошибка OpenAI: {str(e)}]"


async def _stream_ollama(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    temperature: float
) -> AsyncGenerator[str, None]:
    """Stream from Ollama API."""
    base_url = settings.OLLAMA_BASE_URL.rstrip("/")
    
    timeout = httpx.Timeout(max(settings.LLM_TIMEOUT, 180), connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            async with client.stream(
                "POST",
                f"{base_url}/api/chat",
                json={
                    "model": settings.OLLAMA_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "stream": True,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": temperature
                    }
                }
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    try:
                        parsed = json.loads(line)
                        content = parsed.get("message", {}).get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        pass
        except Exception as e:
            logger.error(f"Ollama streaming error: {e}")
            yield f"\n\n[Ошибка Ollama: {str(e)}]"


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
            system_prompt=ANALYSIS_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=settings.LLM_MAX_TOKENS,
            temperature=settings.LLM_TEMPERATURE
        )
        
        # Ensure response is clean (defense in depth)
        cleaned_response = clean_think_tags(response)
        
        return AnalysisExplanation(
            text=cleaned_response,
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
    
    # Build style info
    style_text = ""
    if top_styles and len(top_styles) > 0:
        top_style = top_styles[0]
        style_name = top_style.name.replace("_", " ").title()
        style_text = f" Художественный стиль наиболее близок к направлению {style_name}."
    
    # Build genre info
    genre_text = ""
    if top_genres and len(top_genres) > 0:
        top_genre = top_genres[0]
        genre_name = top_genre.name.replace("_", " ").title()
        genre_text = f" Жанр определён как {genre_name}."
    
    # Other artists for parallels
    parallels_text = ""
    if len(top_artists) > 1:
        parallels = []
        for a in top_artists[1:3]:
            name = a.artist_slug.replace("-", " ").title()
            parallels.append(f"**{name}**: стилистическое сходство в технике исполнения")
        parallels_text = "\n".join(parallels)
    
    explanation_text = f"""## 🎨 Художественный анализ
Данное произведение демонстрирует характерные черты, ассоциируемые с творчеством {artist_name}.{style_text}{genre_text}

### Ключевые характеристики
- **Техника**: Требуется детальный анализ
- **Палитра**: Требуется детальный анализ
- **Композиция**: Требуется детальный анализ

### О вероятном авторе
{artist_name} — художник, чей стиль наиболее соответствует анализируемому произведению. Для получения подробного описания биографии, техники и контекста творчества включите LLM-провайдер в настройках системы.

### Стилистические параллели
{parallels_text if parallels_text else "Требуется LLM для анализа параллелей"}

### Историко-художественный контекст
Для получения полного историко-художественного анализа необходимо подключение к LLM-провайдеру."""
    
    return AnalysisExplanation(
        text=explanation_text,
        source="stub"
    )
