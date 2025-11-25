"""Services package."""
from app.services.classifier import get_top_artists, get_full_predictions
from app.services.llm_service import generate_explanation
from app.services.comfyui_service import generate_images_with_prompt
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
    "get_full_predictions",
    "generate_explanation",
    "generate_images_with_prompt",
    "get_user_by_email",
    "get_user_by_username",
    "get_user_by_id",
    "create_user",
    "authenticate_user",
    "create_user_token",
]
