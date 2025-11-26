"""History API endpoint."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.history import AnalysisHistory
from app.models.schemas import (
    HistoryItemResponse,
    HistoryListResponse,
    ErrorResponse,
)

router = APIRouter(prefix="/history", tags=["History"])


@router.get(
    "",
    response_model=HistoryListResponse,
    responses={
        401: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def get_history(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get user's analysis history.
    
    Returns list of previous analyses for the current user.
    """
    try:
        # If this is a guest account (created via /auth/guest) we return empty history
        try:
            uname = (current_user.username or '').lower()
            email = (current_user.email or '').lower()
            if uname.startswith('guest_') or email.startswith('guest_'):
                return HistoryListResponse(success=True, items=[], total=0)
        except Exception:
            pass
        # Get total count
        total = db.query(AnalysisHistory).filter(
            AnalysisHistory.user_id == current_user.id
        ).count()
        
        # Get items with pagination
        items = db.query(AnalysisHistory).filter(
            AnalysisHistory.user_id == current_user.id
        ).order_by(
            AnalysisHistory.created_at.desc()
        ).offset(offset).limit(limit).all()
        
        return HistoryListResponse(
            success=True,
            items=[
                HistoryItemResponse(
                    id=item.id,
                    image_url=item.image_url or f"/api/uploads/{item.image_filename}",
                    top_artist_slug=item.top_artist_slug,
                    created_at=item.created_at,
                    analysis_result=item.analysis_result,
                )
                for item in items
            ],
            total=total,
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch history: {str(e)}"
        )


@router.delete(
    "/{history_id}",
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def delete_history_item(
    history_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a history item.
    
    Only the owner can delete their history items.
    """
    try:
        item = db.query(AnalysisHistory).filter(
            AnalysisHistory.id == history_id,
            AnalysisHistory.user_id == current_user.id
        ).first()
        
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="History item not found"
            )
        
        db.delete(item)
        db.commit()
        
        return {"success": True, "message": "History item deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete history item: {str(e)}"
        )


@router.delete(
    "",
    responses={
        401: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def clear_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Clear all history for the current user.
    """
    try:
        db.query(AnalysisHistory).filter(
            AnalysisHistory.user_id == current_user.id
        ).delete()
        db.commit()
        
        return {"success": True, "message": "History cleared"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear history: {str(e)}"
        )
