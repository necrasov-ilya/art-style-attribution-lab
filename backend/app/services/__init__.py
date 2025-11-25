"""Services package."""
from app.services.classifier import get_top_artists
from app.services.llm_service import generate_explanation
from app.services.comfyui_service import generate_thumbnails
from app.services.auth_service import (
    get_user_by_email,
    get_user_by_username,
    get_user_by_id,
    create_user,
    authenticate_user,
    create_user_token,
)

__all__ = [
    "get_top_artists",
    "generate_explanation",
    "generate_thumbnails",
    "get_user_by_email",
    "get_user_by_username",
    "get_user_by_id",
    "create_user",
    "authenticate_user",
    "create_user_token",
]
