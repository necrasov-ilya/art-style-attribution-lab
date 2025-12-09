"""Collaborative session API endpoints for shared analysis discussions."""
import uuid
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.schemas import (
    CollaborativeSessionCreate,
    CollaborativeSessionResponse,
    CollaborativeSessionPublic,
    CollaborativeQuestionRequest,
    CollaborativeQuestionResponse,
    CollaborativeHeartbeatResponse,
    CollaborativeCloseResponse,
    CollaborativeUpdateRequest,
    CollaborativeUpdateResponse,
    ErrorResponse,
)
from app.services import collaborative_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/collaborative", tags=["Collaborative"])


@router.post("", response_model=CollaborativeSessionResponse)
async def create_session(
    request: CollaborativeSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new collaborative session for sharing analysis.
    
    Only authenticated (non-guest) users can create sessions.
    Each user can have only one active session at a time.
    """
    # Check if user is a guest
    if current_user.email.startswith("guest_"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Гости не могут создавать совместные сессии"
        )
    
    # Close any existing active session before creating new one
    existing = collaborative_service.get_user_active_session(db, current_user.id)
    if existing:
        collaborative_service.close_session(db, existing.id, current_user.id)
    
    # Create new session with current analysis data
    session = collaborative_service.create_session(
        db=db,
        owner_id=current_user.id,
        analysis_data=request.analysis_data,
        image_url=request.image_url,
        duration_minutes=40
    )
    
    return CollaborativeSessionResponse(
        id=session.id,
        image_url=session.image_url,
        analysis_data=session.analysis_data,
        created_at=session.created_at,
        expires_at=session.expires_at,
        remaining_seconds=session.remaining_seconds,
        active_viewers=0,
        is_active=session.is_active
    )


@router.get("/{session_id}", response_model=CollaborativeSessionPublic)
async def get_session(
    session_id: str,
    db: Session = Depends(get_db)
):
    """Get public session info for guests joining via link.
    
    This endpoint is public (no auth required).
    """
    session = collaborative_service.get_active_session(db, session_id)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сессия не найдена или истекла"
        )
    
    # Extract top predictions for display
    artists = session.analysis_data.get("top_artists", [])
    styles = session.analysis_data.get("top_styles", [])
    genres = session.analysis_data.get("top_genres", [])
    
    top_artist = artists[0].get("artist_slug", "unknown").replace("-", " ").title() if artists else None
    top_style = styles[0].get("name", "unknown").replace("_", " ").title() if styles else None
    top_genre = genres[0].get("name", "unknown").replace("_", " ").title() if genres else None
    
    # Check if deep analysis was performed
    deep_analysis = session.analysis_data.get("deep_analysis_result")
    has_deep_analysis = bool(deep_analysis)
    
    return CollaborativeSessionPublic(
        id=session.id,
        image_url=session.image_url,
        top_artist=top_artist,
        top_style=top_style,
        top_genre=top_genre,
        remaining_seconds=session.remaining_seconds,
        is_active=session.is_active,
        has_deep_analysis=has_deep_analysis
    )


@router.get("/{session_id}/full", response_model=CollaborativeSessionResponse)
async def get_session_full(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get full session info (for session owner only)."""
    session = collaborative_service.get_session(db, session_id)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сессия не найдена"
        )
    
    if session.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещён"
        )
    
    return CollaborativeSessionResponse(
        id=session.id,
        image_url=session.image_url,
        analysis_data=session.analysis_data,
        created_at=session.created_at,
        expires_at=session.expires_at,
        remaining_seconds=session.remaining_seconds,
        active_viewers=collaborative_service.get_viewer_count(session.id),
        is_active=session.is_active
    )


@router.post("/{session_id}/ask", response_model=CollaborativeQuestionResponse)
async def ask_question(
    session_id: str,
    request: CollaborativeQuestionRequest,
    db: Session = Depends(get_db)
):
    """Ask a question about the analysis (non-streaming).
    
    This endpoint is public (no auth required).
    Use /ask/stream for streaming responses.
    """
    session = collaborative_service.get_active_session(db, session_id)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сессия не найдена или истекла"
        )
    
    # Generate answer
    answer = await collaborative_service.answer_question(session, request.question)
    
    return CollaborativeQuestionResponse(
        success=True,
        question=request.question,
        answer=answer
    )


@router.post("/{session_id}/ask/stream")
async def ask_question_stream(
    session_id: str,
    request: CollaborativeQuestionRequest,
    db: Session = Depends(get_db)
):
    """Ask a question and get a streaming response via SSE.
    
    Returns Server-Sent Events with the answer being generated in real-time.
    """
    session = collaborative_service.get_active_session(db, session_id)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сессия не найдена или истекла"
        )
    
    async def event_generator():
        """Generate SSE events from LLM streaming response."""
        try:
            async for chunk in collaborative_service.answer_question_streaming(session, request.question):
                # SSE format: data: <content>\n\n
                yield f"data: {chunk}\n\n"
            # Send done signal
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"data: [ERROR] {str(e)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@router.post("/{session_id}/heartbeat", response_model=CollaborativeHeartbeatResponse)
async def heartbeat(
    session_id: str,
    viewer_id: Optional[str] = Query(default=None),
    db: Session = Depends(get_db)
):
    """Update viewer presence and get session status.
    
    Called periodically (every 30s) by guests viewing the session.
    """
    session = collaborative_service.get_active_session(db, session_id)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сессия не найдена или истекла"
        )
    
    # Generate viewer ID if not provided
    if not viewer_id:
        viewer_id = str(uuid.uuid4())
    
    # Register presence
    active_count = collaborative_service.register_viewer(session_id, viewer_id)
    
    # Update session in DB periodically
    collaborative_service.update_session_viewer_count(db, session_id)
    
    # Check if deep analysis is available
    has_deep_analysis = bool(
        session.analysis_data and 
        session.analysis_data.get('deep_analysis_result')
    )
    
    return CollaborativeHeartbeatResponse(
        success=True,
        active_viewers=active_count,
        remaining_seconds=session.remaining_seconds,
        has_deep_analysis=has_deep_analysis
    )


@router.get("/{session_id}/viewers", response_model=CollaborativeHeartbeatResponse)
async def get_viewers(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current viewer count (for session owner)."""
    session = collaborative_service.get_session(db, session_id)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сессия не найдена"
        )
    
    if session.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещён"
        )
    
    return CollaborativeHeartbeatResponse(
        success=True,
        active_viewers=collaborative_service.get_viewer_count(session_id),
        remaining_seconds=session.remaining_seconds
    )


@router.delete("/{session_id}", response_model=CollaborativeCloseResponse)
async def close_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Close a collaborative session (owner only)."""
    success = collaborative_service.close_session(db, session_id, current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сессия не найдена или вы не являетесь владельцем"
        )
    
    return CollaborativeCloseResponse(success=True, message="Сессия закрыта")


@router.patch("/{session_id}", response_model=CollaborativeUpdateResponse)
async def update_session(
    session_id: str,
    request: CollaborativeUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update session analysis data (e.g., after deep analysis)."""
    success = collaborative_service.update_session_analysis(
        db, session_id, current_user.id, request.analysis_data
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сессия не найдена или вы не являетесь владельцем"
        )
    
    # Check if deep analysis is included
    deep_analysis = request.analysis_data.get("deep_analysis_result", {})
    has_deep_analysis = bool(deep_analysis and deep_analysis.get("summary"))
    
    return CollaborativeUpdateResponse(success=True, has_deep_analysis=has_deep_analysis)
