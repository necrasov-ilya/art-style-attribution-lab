"""File validation with magic number verification."""
from pathlib import Path
from typing import Optional
from fastapi import HTTPException, UploadFile, status


# Magic number signatures for supported image formats
IMAGE_SIGNATURES = {
    b'\xFF\xD8\xFF': 'jpeg',  # JPEG
    b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A': 'png',  # PNG
    b'RIFF': 'webp',  # WebP (needs additional check)
    b'BM': 'bmp',  # BMP
}

ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
ALLOWED_CONTENT_TYPES = {'image/jpeg', 'image/png', 'image/webp', 'image/bmp'}
MAX_FILENAME_LENGTH = 255


def verify_image_magic_number(content: bytes) -> Optional[str]:
    """
    Verify file is a valid image by checking magic numbers.

    Returns the detected format or None if invalid.
    """
    if len(content) < 12:
        return None

    # Check PNG
    if content[:8] == b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A':
        return 'png'

    # Check JPEG
    if content[:3] == b'\xFF\xD8\xFF':
        return 'jpeg'

    # Check BMP
    if content[:2] == b'BM':
        return 'bmp'

    # Check WebP (RIFF header + WEBP signature)
    if content[:4] == b'RIFF' and content[8:12] == b'WEBP':
        return 'webp'

    return None


def validate_filename(filename: Optional[str]) -> str:
    """
    Validate filename for security issues.

    Raises HTTPException if filename is invalid.
    Returns sanitized filename.
    """
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required"
        )

    # Check length
    if len(filename) > MAX_FILENAME_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Filename too long (max {MAX_FILENAME_LENGTH} characters)"
        )

    # Check for path traversal attempts
    if '..' in filename or '/' in filename or '\\' in filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename: path traversal detected"
        )

    # Check for null bytes
    if '\x00' in filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename: null byte detected"
        )

    return filename


async def validate_image_upload(
    file: UploadFile,
    max_size: int = 10 * 1024 * 1024  # 10MB default
) -> bytes:
    """
    Comprehensive validation of uploaded image file.

    Checks:
    - Filename validity
    - File extension
    - Content-Type header
    - File size
    - Magic number verification

    Returns file content if valid, raises HTTPException otherwise.
    """
    # Validate filename
    filename = validate_filename(file.filename)

    # Check extension
    file_ext = Path(filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file extension. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Check content type
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid content type: {file.content_type}"
        )

    # Read content
    content = await file.read()

    # Check size
    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {max_size // (1024*1024)}MB"
        )

    # Verify magic number
    detected_format = verify_image_magic_number(content)
    if not detected_format:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image file: unrecognized format or corrupted data"
        )

    # Verify format matches extension
    ext_to_format = {
        '.jpg': 'jpeg',
        '.jpeg': 'jpeg',
        '.png': 'png',
        '.webp': 'webp',
        '.bmp': 'bmp',
    }

    expected_format = ext_to_format.get(file_ext)
    if expected_format and detected_format != expected_format:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File extension mismatch: file is {detected_format} but extension is {file_ext}"
        )

    return content
