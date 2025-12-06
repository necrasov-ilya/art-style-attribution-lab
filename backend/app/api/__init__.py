"""API package."""
from fastapi import APIRouter
from fastapi.staticfiles import StaticFiles

from app.api.auth import router as auth_router
from app.api.analyze import router as analyze_router
from app.api.history import router as history_router
from app.api.deep_analysis import router as deep_analysis_router
from app.api.collaborative import router as collaborative_router

api_router = APIRouter(prefix="/api")
api_router.include_router(auth_router)
api_router.include_router(analyze_router)
api_router.include_router(history_router)
api_router.include_router(deep_analysis_router)
api_router.include_router(collaborative_router)

__all__ = ["api_router"]
