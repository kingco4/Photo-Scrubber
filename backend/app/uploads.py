from __future__ import annotations

import io
import pathlib
from typing import Final, Optional

from fastapi import HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError

from .config import (
    ALLOWED_CONTENT_TYPES,
    CONTENT_TYPE_ALIASES,
    CONTENT_TYPE_TO_EXTENSIONS,
    CONTENT_TYPE_TO_FORMATS,
    EXTENSION_TO_CONTENT_TYPE,
    HEIC_BRANDS,
    HEIF_BRANDS,
    MAX_IMAGE_HEIGHT,
    MAX_IMAGE_PIXELS,
    MAX_IMAGE_WIDTH,
    MAX_UPLOAD_BYTES,
    MIN_IMAGE_HEIGHT,
    MIN_IMAGE_WIDTH,
    register_heif_opener,
)


HEIF_CONTENT_TYPES: Final[set[str]] = {"image/heic", "image/heif"}


def detect_image_signature(raw: bytes) -> str | None:
    if raw.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if raw.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(raw) >= 12 and raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        return "image/webp"
    if len(raw) >= 16 and raw[4:8] == b"ftyp":
        brands = {raw[8:12].decode("ascii", errors="ignore").lower()}
        compatible_brands = raw[16:min(len(raw), 64)]
        for index in range(0, len(compatible_brands) - 3, 4):
            brands.add(compatible_brands[index:index + 4].decode("ascii", errors="ignore").lower())
        if brands & HEIC_BRANDS:
            return "image/heic"
        if brands & HEIF_BRANDS:
            return "image/heif"
    return None


def normalize_upload_filename(filename: str) -> str:
    normalized = filename.strip().replace("\x00", "")
    normalized = normalized.split("/")[-1].split("\\")[-1]
    if normalized in {"", ".", ".."}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file must have a valid filename.")
    if any(ord(char) < 32 for char in normalized):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Filename contains unsupported control characters.")
    return normalized


def normalize_declared_content_type(content_type: Optional[str]) -> Optional[str]:
    if not content_type:
        return None
    normalized = content_type.strip().lower()
    if normalized in {"", "application/octet-stream"}:
        return None
    return CONTENT_TYPE_ALIASES.get(normalized, normalized)


def validate_non_critical_upload_checks(filename: str, declared_content_type: Optional[str], suffix: str) -> None:
    if len(filename) > 255:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Filename must be at most 255 characters.")
    if declared_content_type is not None and declared_content_type not in ALLOWED_CONTENT_TYPES:
        allowed = ", ".join(sorted(ALLOWED_CONTENT_TYPES))
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=f"Unsupported file type. Allowed types: {allowed}.")
    extension_content_type = EXTENSION_TO_CONTENT_TYPE.get(suffix)
    if extension_content_type is None:
        allowed_extensions = ", ".join(sorted(EXTENSION_TO_CONTENT_TYPE))
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=f"Unsupported filename extension. Allowed extensions: {allowed_extensions}.")
    if declared_content_type is not None and suffix not in CONTENT_TYPE_TO_EXTENSIONS.get(declared_content_type, set()):
        allowed_extensions = ", ".join(sorted(CONTENT_TYPE_TO_EXTENSIONS.get(declared_content_type, set())))
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=f"Filename extension does not match {declared_content_type}. Allowed extensions: {allowed_extensions}.")


def validate_image_dimensions(width: int, height: int) -> None:
    if width <= 0 or height <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image dimensions must be positive.")
    if width < MIN_IMAGE_WIDTH or height < MIN_IMAGE_HEIGHT:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Image must be at least {MIN_IMAGE_WIDTH}x{MIN_IMAGE_HEIGHT} pixels.")
    if width > MAX_IMAGE_WIDTH or height > MAX_IMAGE_HEIGHT:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=f"Image dimensions exceed the {MAX_IMAGE_WIDTH}x{MAX_IMAGE_HEIGHT} limit.")
    if width * height > MAX_IMAGE_PIXELS:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=f"Image exceeds the {MAX_IMAGE_PIXELS} pixel limit.")


async def read_and_validate_upload(file: UploadFile, *, skip_non_critical_checks: bool = False) -> Image.Image:
    raw_filename = file.filename or ""
    filename = normalize_upload_filename(raw_filename) if raw_filename.strip() else "upload.bin"
    declared_content_type = normalize_declared_content_type(file.content_type)
    suffix = pathlib.Path(filename).suffix.lower()
    extension_content_type = EXTENSION_TO_CONTENT_TYPE.get(suffix)
    if not skip_non_critical_checks:
        validate_non_critical_upload_checks(filename, declared_content_type, suffix)
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=f"Uploaded file exceeds the {MAX_UPLOAD_BYTES} byte limit.")
    detected_content_type = detect_image_signature(raw)
    if detected_content_type is None:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Uploaded file does not have a supported image signature.")
    effective_content_type = declared_content_type or extension_content_type or detected_content_type
    if not skip_non_critical_checks and detected_content_type != effective_content_type:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=f"Uploaded file signature does not match expected type {effective_content_type}.")
    if detected_content_type in HEIF_CONTENT_TYPES and register_heif_opener is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="HEIC/HEIF support is not installed on the server. Install backend requirements to enable it.")
    try:
        pil = Image.open(io.BytesIO(raw))
        pil.load()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is not a valid image.") from exc
    if not skip_non_critical_checks and getattr(pil, "n_frames", 1) != 1:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Animated or multi-frame image uploads are not supported.")
    validate_image_dimensions(*pil.size)
    actual_format = (pil.format or "").upper()
    expected_formats = CONTENT_TYPE_TO_FORMATS.get(effective_content_type, set())
    if not skip_non_critical_checks and expected_formats and actual_format not in expected_formats:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=f"Uploaded file content does not match expected type {effective_content_type}.")
    return pil
