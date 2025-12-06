"""Collaborative session service for shared analysis discussions.

This service manages collaborative sessions where authenticated users can share
their analysis and allow guests to ask questions via LLM.
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any, AsyncGenerator
from sqlalchemy.orm import Session

from app.models.collaborative import CollaborativeSession
from app.services.llm_client import get_cached_provider, LLMError, clean_think_tags
from app.services.prompts import build_collaborative_qa_prompt, COLLABORATIVE_QA_SYSTEM_PROMPT
from app.core.config import settings

import httpx

logger = logging.getLogger(__name__)

# In-memory storage for active viewers (simplified approach)
# In production, use Redis for distributed state
_active_viewers: Dict[str, Dict[str, datetime]] = {}  # {session_id: {viewer_id: last_seen}}


def create_session(
    db: Session,
    owner_id: int,
    analysis_data: dict,
    image_url: str,
    duration_minutes: int = 40
) -> CollaborativeSession:
    """Create a new collaborative session."""
    session = CollaborativeSession.create_session(
        owner_id=owner_id,
        analysis_data=analysis_data,
        image_url=image_url,
        duration_minutes=duration_minutes
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    logger.info(f"Created collaborative session {session.id} for user {owner_id}")
    return session


def get_session(db: Session, session_id: str) -> Optional[CollaborativeSession]:
    """Get a session by ID."""
    return db.query(CollaborativeSession).filter(
        CollaborativeSession.id == session_id
    ).first()


def get_active_session(db: Session, session_id: str) -> Optional[CollaborativeSession]:
    """Get an active (not expired, not closed) session."""
    session = get_session(db, session_id)
    if session and session.is_active and not session.is_expired:
        return session
    return None


def close_session(db: Session, session_id: str, owner_id: int) -> bool:
    """Close a session (only owner can close)."""
    session = db.query(CollaborativeSession).filter(
        CollaborativeSession.id == session_id,
        CollaborativeSession.owner_id == owner_id
    ).first()
    
    if session:
        session.is_active = False
        db.commit()
        # Clean up viewers
        if session_id in _active_viewers:
            del _active_viewers[session_id]
        logger.info(f"Closed collaborative session {session_id}")
        return True
    return False


def update_session_analysis(db: Session, session_id: str, owner_id: int, analysis_data: dict) -> bool:
    """Update the analysis data for a session (e.g., after deep analysis)."""
    session = db.query(CollaborativeSession).filter(
        CollaborativeSession.id == session_id,
        CollaborativeSession.owner_id == owner_id,
        CollaborativeSession.is_active == True
    ).first()
    
    if session:
        session.analysis_data = analysis_data
        db.commit()
        logger.info(f"Updated analysis data for session {session_id}")
        return True
    return False


def get_user_active_session(db: Session, owner_id: int) -> Optional[CollaborativeSession]:
    """Get user's currently active session (if any)."""
    return db.query(CollaborativeSession).filter(
        CollaborativeSession.owner_id == owner_id,
        CollaborativeSession.is_active == True,
        CollaborativeSession.expires_at > datetime.utcnow()
    ).first()


def register_viewer(session_id: str, viewer_id: str) -> int:
    """Register a viewer presence and return active count."""
    now = datetime.utcnow()
    
    if session_id not in _active_viewers:
        _active_viewers[session_id] = {}
    
    _active_viewers[session_id][viewer_id] = now
    
    # Clean up stale viewers (> 60 seconds)
    _cleanup_stale_viewers(session_id)
    
    return len(_active_viewers.get(session_id, {}))


def get_viewer_count(session_id: str) -> int:
    """Get current active viewer count."""
    _cleanup_stale_viewers(session_id)
    return len(_active_viewers.get(session_id, {}))


def _cleanup_stale_viewers(session_id: str):
    """Remove viewers who haven't sent heartbeat in 60 seconds."""
    if session_id not in _active_viewers:
        return
    
    now = datetime.utcnow()
    stale_threshold = 60  # seconds
    
    _active_viewers[session_id] = {
        viewer_id: last_seen
        for viewer_id, last_seen in _active_viewers[session_id].items()
        if (now - last_seen).total_seconds() < stale_threshold
    }


def update_session_viewer_count(db: Session, session_id: str):
    """Update the viewer count in database."""
    count = get_viewer_count(session_id)
    session = get_session(db, session_id)
    if session:
        session.active_viewers = count
        db.commit()


async def answer_question(
    session: CollaborativeSession,
    question: str
) -> str:
    """Generate an answer to a question about the analysis using LLM."""
    try:
        provider = get_cached_provider()
        
        # Build context from analysis data
        user_prompt = build_collaborative_qa_prompt(
            analysis_data=session.analysis_data,
            question=question
        )
        
        response = await provider.generate(
            system_prompt=COLLABORATIVE_QA_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=1024,
            temperature=0.7
        )
        
        return clean_think_tags(response)
        
    except LLMError as e:
        logger.error(f"LLM error answering question: {e}")
        return "Извините, произошла ошибка при генерации ответа. Попробуйте ещё раз."
    except Exception as e:
        logger.error(f"Unexpected error answering question: {e}")
        return "Произошла непредвиденная ошибка. Попробуйте позже."


async def answer_question_streaming(
    session: CollaborativeSession,
    question: str
) -> AsyncGenerator[str, None]:
    """Generate a streaming answer to a question using SSE.
    
    Yields chunks of text as they are generated by the LLM.
    """
    try:
        # Build context from analysis data
        user_prompt = build_collaborative_qa_prompt(
            analysis_data=session.analysis_data,
            question=question
        )
        
        provider_name = settings.LLM_PROVIDER.lower()
        
        if provider_name == "openrouter":
            async for chunk in _stream_openrouter(user_prompt):
                yield chunk
        elif provider_name == "openai":
            async for chunk in _stream_openai(user_prompt):
                yield chunk
        elif provider_name == "ollama":
            async for chunk in _stream_ollama(user_prompt):
                yield chunk
        else:
            yield "Streaming не поддерживается для текущего LLM провайдера."
            
    except Exception as e:
        logger.error(f"Streaming error: {e}")
        yield f"Ошибка: {str(e)}"


async def _stream_openrouter(user_prompt: str) -> AsyncGenerator[str, None]:
    """Stream response from OpenRouter API."""
    if not settings.OPENROUTER_API_KEY:
        yield "OpenRouter API ключ не настроен."
        return
    
    timeout = httpx.Timeout(settings.LLM_TIMEOUT, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
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
                    {"role": "system", "content": COLLABORATIVE_QA_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                "max_tokens": 1024,
                "temperature": 0.7,
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
                        import json
                        parsed = json.loads(data)
                        delta = parsed.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            # Yield content directly - preserve spaces
                            yield content
                    except:
                        pass


async def _stream_openai(user_prompt: str) -> AsyncGenerator[str, None]:
    """Stream response from OpenAI API."""
    if not settings.OPENAI_API_KEY:
        yield "OpenAI API ключ не настроен."
        return
    
    timeout = httpx.Timeout(settings.LLM_TIMEOUT, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
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
                    {"role": "system", "content": COLLABORATIVE_QA_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                "max_tokens": 1024,
                "temperature": 0.7,
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
                        import json
                        parsed = json.loads(data)
                        delta = parsed.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except:
                        pass


async def _stream_ollama(user_prompt: str) -> AsyncGenerator[str, None]:
    """Stream response from Ollama API."""
    base_url = settings.OLLAMA_BASE_URL.rstrip("/")
    
    timeout = httpx.Timeout(max(settings.LLM_TIMEOUT, 180), connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream(
            "POST",
            f"{base_url}/api/chat",
            json={
                "model": settings.OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": COLLABORATIVE_QA_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                "stream": True,
                "options": {
                    "num_predict": 1024,
                    "temperature": 0.7
                }
            }
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                try:
                    import json
                    parsed = json.loads(line)
                    content = parsed.get("message", {}).get("content", "")
                    if content:
                        # Yield content directly - preserve spaces
                        yield content
                except:
                    pass
