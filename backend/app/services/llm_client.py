"""LLM client with support for multiple providers: OpenAI, OpenRouter, Ollama.

This module provides a unified interface for LLM calls regardless of the provider.
Provider is selected via LLM_PROVIDER environment variable.
"""
import base64
import logging
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, List, Union

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def clean_think_tags(text: str) -> str:
    """Remove <think>...</think> and <thinking>...</thinking> blocks from LLM response."""
    if not text:
        return ""
    
    patterns = [
        r'<think[^>]*>[\s\S]*?</think>',
        r'<thinking[^>]*>[\s\S]*?</thinking>',
        r'<think[^>]*>[\s\S]*$',
        r'<thinking[^>]*>[\s\S]*$',
    ]
    
    for pattern in patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7
    ) -> str:
        """Generate a response from the LLM.
        
        Args:
            system_prompt: System message defining LLM behavior
            user_prompt: User message with the actual query
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0-1)
            
        Returns:
            Generated text response
            
        Raises:
            LLMError: If generation fails
        """
        pass


class LLMError(Exception):
    """Exception raised when LLM call fails."""
    pass


class OpenAIProvider(LLMProvider):
    """OpenAI API provider (GPT models)."""
    
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.model = settings.OPENAI_MODEL
        self.base_url = "https://api.openai.com/v1"
        
        if not self.api_key:
            raise LLMError("OPENAI_API_KEY is not configured")
    
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7
    ) -> str:
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        "max_tokens": max_tokens,
                        "temperature": temperature
                    }
                )
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                return clean_think_tags(content)
                
            except httpx.HTTPStatusError as e:
                logger.error(f"OpenAI API error: {e.response.status_code} - {e.response.text}")
                raise LLMError(f"OpenAI API error: {e.response.status_code}")
            except Exception as e:
                logger.error(f"OpenAI request failed: {e}")
                raise LLMError(f"OpenAI request failed: {str(e)}")


class OpenRouterProvider(LLMProvider):
    """OpenRouter API provider (access to multiple models)."""
    
    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        self.model = settings.OPENROUTER_MODEL
        self.base_url = "https://openrouter.ai/api/v1"
        
        if not self.api_key:
            raise LLMError("OPENROUTER_API_KEY is not configured")
    
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7
    ) -> str:
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://art-style-attribution-lab.local",
                        "X-Title": "Art Style Attribution Lab"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        "max_tokens": max_tokens,
                        "temperature": temperature
                    }
                )
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                return clean_think_tags(content)
                
            except httpx.HTTPStatusError as e:
                logger.error(f"OpenRouter API error: {e.response.status_code} - {e.response.text}")
                raise LLMError(f"OpenRouter API error: {e.response.status_code}")
            except Exception as e:
                logger.error(f"OpenRouter request failed: {e}")
                raise LLMError(f"OpenRouter request failed: {str(e)}")


class OllamaProvider(LLMProvider):
    """Ollama local LLM provider."""
    
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self.model = settings.OLLAMA_MODEL
    
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7
    ) -> str:
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        "stream": False,
                        "options": {
                            "num_predict": max_tokens,
                            "temperature": temperature
                        }
                    }
                )
                response.raise_for_status()
                data = response.json()
                content = data["message"]["content"]
                return clean_think_tags(content)
                
            except httpx.ConnectError:
                logger.error(f"Cannot connect to Ollama at {self.base_url}")
                raise LLMError(f"Cannot connect to Ollama. Is it running at {self.base_url}?")
            except httpx.HTTPStatusError as e:
                logger.error(f"Ollama API error: {e.response.status_code} - {e.response.text}")
                raise LLMError(f"Ollama API error: {e.response.status_code}")
            except Exception as e:
                logger.error(f"Ollama request failed: {e}")
                raise LLMError(f"Ollama request failed: {str(e)}")


class StubProvider(LLMProvider):
    """Stub provider that returns a placeholder message."""
    
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7
    ) -> str:
        return (
            "LLM analysis is not configured. "
            "Set LLM_PROVIDER in your environment to enable AI-powered explanations. "
            "Supported providers: openai, openrouter, ollama."
        )


def get_llm_provider() -> LLMProvider:
    """Factory function to get the configured LLM provider.
    
    Returns:
        LLMProvider instance based on LLM_PROVIDER setting
        
    Raises:
        LLMError: If provider configuration is invalid
    """
    provider_name = settings.LLM_PROVIDER.lower()
    
    if provider_name == "openai":
        return OpenAIProvider()
    elif provider_name == "openrouter":
        return OpenRouterProvider()
    elif provider_name == "ollama":
        return OllamaProvider()
    elif provider_name == "none":
        return StubProvider()
    else:
        logger.warning(f"Unknown LLM provider: {provider_name}, using stub")
        return StubProvider()


# Singleton-like cached provider
_cached_provider: Optional[LLMProvider] = None


def get_cached_provider() -> LLMProvider:
    """Get or create a cached LLM provider instance.
    
    This avoids recreating the provider on every request.
    """
    global _cached_provider
    if _cached_provider is None:
        _cached_provider = get_llm_provider()
    return _cached_provider


def reset_provider_cache():
    """Reset the cached provider (useful for testing or config changes)."""
    global _cached_provider
    _cached_provider = None


# ============ Vision LLM Support ============

def encode_image_to_base64(image_path: str) -> str:
    """Read image file and encode to base64."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def get_image_media_type(image_path: str) -> str:
    """Determine media type from file extension."""
    ext = Path(image_path).suffix.lower()
    media_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
    }
    return media_types.get(ext, "image/jpeg")


async def generate_with_vision(
    image_path: str,
    prompt: str,
    system_prompt: str = "You are an expert art analyst. Analyze the image and respond in Russian.",
    max_tokens: int = 1024,
    temperature: float = 0.7
) -> str:
    """Generate LLM response with image input using Vision API.
    
    Uses VISION_LLM_PROVIDER setting to select the provider.
    Falls back to text-only if vision is not available.
    
    Args:
        image_path: Path to image file
        prompt: User prompt describing what to analyze
        system_prompt: System message
        max_tokens: Maximum tokens in response
        temperature: Sampling temperature
        
    Returns:
        Generated text response
    """
    if not settings.VISION_LLM_ENABLED:
        logger.warning("Vision LLM is disabled, returning placeholder")
        return "Vision LLM не настроен. Установите VISION_LLM_ENABLED=true в .env"
    
    provider = settings.VISION_LLM_PROVIDER.lower()
    
    if provider == "openrouter":
        return await _vision_openrouter(image_path, prompt, system_prompt, max_tokens, temperature)
    elif provider == "openai":
        return await _vision_openai(image_path, prompt, system_prompt, max_tokens, temperature)
    else:
        logger.warning(f"Vision provider '{provider}' not supported")
        return "Vision LLM провайдер не поддерживается."


async def _vision_openrouter(
    image_path: str,
    prompt: str,
    system_prompt: str,
    max_tokens: int,
    temperature: float
) -> str:
    """Call OpenRouter Vision API."""
    if not settings.OPENROUTER_API_KEY:
        raise LLMError("OPENROUTER_API_KEY is not configured")
    
    image_b64 = encode_image_to_base64(image_path)
    media_type = get_image_media_type(image_path)
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://art-style-attribution-lab.local",
                    "X-Title": "Art Style Attribution Lab"
                },
                json={
                    "model": settings.OPENROUTER_VISION_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:{media_type};base64,{image_b64}"
                                    }
                                },
                                {
                                    "type": "text",
                                    "text": prompt
                                }
                            ]
                        }
                    ],
                    "max_tokens": max_tokens,
                    "temperature": temperature
                }
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            return clean_think_tags(content)
            
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenRouter Vision API error: {e.response.status_code} - {e.response.text}")
            raise LLMError(f"OpenRouter Vision API error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"OpenRouter Vision request failed: {e}")
            raise LLMError(f"OpenRouter Vision request failed: {str(e)}")


async def _vision_openai(
    image_path: str,
    prompt: str,
    system_prompt: str,
    max_tokens: int,
    temperature: float
) -> str:
    """Call OpenAI Vision API (GPT-4o)."""
    if not settings.OPENAI_API_KEY:
        raise LLMError("OPENAI_API_KEY is not configured")
    
    image_b64 = encode_image_to_base64(image_path)
    media_type = get_image_media_type(image_path)
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4o-mini",  # or gpt-4o for better quality
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:{media_type};base64,{image_b64}"
                                    }
                                },
                                {
                                    "type": "text",
                                    "text": prompt
                                }
                            ]
                        }
                    ],
                    "max_tokens": max_tokens,
                    "temperature": temperature
                }
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            return clean_think_tags(content)
            
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenAI Vision API error: {e.response.status_code} - {e.response.text}")
            raise LLMError(f"OpenAI Vision API error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"OpenAI Vision request failed: {e}")
            raise LLMError(f"OpenAI Vision request failed: {str(e)}")
