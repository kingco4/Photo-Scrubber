from __future__ import annotations

import logging
import os
from typing import Final, TypedDict

import cv2

try:
    from pillow_heif import register_heif_opener
except ImportError:
    register_heif_opener = None


def env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


class FileTypeSpec(TypedDict):
    content_type: str
    extensions: tuple[str, ...]
    formats: set[str]
    aliases: tuple[str, ...]


AUTH_USERNAME: Final[str] = os.getenv("PHOTO_SCRUBBER_AUTH_USERNAME", "admin")
AUTH_PASSWORD: Final[str] = os.getenv("PHOTO_SCRUBBER_AUTH_PASSWORD", "changeme")
AUTH_SECRET: Final[str] = os.getenv("PHOTO_SCRUBBER_AUTH_SECRET", "replace-this-secret")
AUTH_ACCESS_CODE: Final[str] = os.getenv("PHOTO_SCRUBBER_AUTH_ACCESS_CODE", "").strip()
TOKEN_TTL_HOURS: Final[int] = max(1, env_int("PHOTO_SCRUBBER_TOKEN_TTL_HOURS", 12))
LOGIN_MAX_ATTEMPTS: Final[int] = max(1, env_int("PHOTO_SCRUBBER_LOGIN_MAX_ATTEMPTS", 5))
LOGIN_BLOCK_SECONDS: Final[int] = max(10, env_int("PHOTO_SCRUBBER_LOGIN_BLOCK_SECONDS", 300))
AUTH_COOKIE_NAME: Final[str] = os.getenv("PHOTO_SCRUBBER_AUTH_COOKIE_NAME", "photo_scrubber_session")
AUTH_COOKIE_SECURE: Final[bool] = os.getenv("PHOTO_SCRUBBER_AUTH_COOKIE_SECURE", "false").strip().lower() in {"1", "true", "yes", "on"}
MAX_UPLOAD_BYTES: Final[int] = max(1, env_int("PHOTO_SCRUBBER_MAX_UPLOAD_BYTES", 15 * 1024 * 1024))
MAX_IMAGE_PIXELS: Final[int] = max(1, env_int("PHOTO_SCRUBBER_MAX_IMAGE_PIXELS", 20_000_000))
MIN_IMAGE_WIDTH: Final[int] = max(1, env_int("PHOTO_SCRUBBER_MIN_IMAGE_WIDTH", 16))
MIN_IMAGE_HEIGHT: Final[int] = max(1, env_int("PHOTO_SCRUBBER_MIN_IMAGE_HEIGHT", 16))
MAX_IMAGE_WIDTH: Final[int] = max(MIN_IMAGE_WIDTH, env_int("PHOTO_SCRUBBER_MAX_IMAGE_WIDTH", 8000))
MAX_IMAGE_HEIGHT: Final[int] = max(MIN_IMAGE_HEIGHT, env_int("PHOTO_SCRUBBER_MAX_IMAGE_HEIGHT", 8000))
LIVE_FRAME_MAX_DIMENSION: Final[int] = max(160, env_int("PHOTO_SCRUBBER_LIVE_FRAME_MAX_DIMENSION", 1280))
LIVE_FRAME_JPEG_QUALITY: Final[int] = max(40, min(95, env_int("PHOTO_SCRUBBER_LIVE_FRAME_JPEG_QUALITY", 72)))
TEXT_DETECTION_MAX_DIMENSION: Final[int] = max(320, env_int("PHOTO_SCRUBBER_TEXT_DETECTION_MAX_DIMENSION", 1800))
FACE_DETECTION_MAX_DIMENSION: Final[int] = max(320, env_int("PHOTO_SCRUBBER_FACE_DETECTION_MAX_DIMENSION", 1600))
VALIDATION_SKIP_THRESHOLD: Final[int] = max(1, env_int("PHOTO_SCRUBBER_VALIDATION_SKIP_THRESHOLD", 20))
LOG_LEVEL: Final[str] = os.getenv("PHOTO_SCRUBBER_LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("photo_scrubber.api")

FILE_TYPE_SPECS: Final[tuple[FileTypeSpec, ...]] = (
    {"content_type": "image/jpeg", "extensions": (".jpg", ".jpeg"), "formats": {"JPEG"}, "aliases": ("image/jpg", "image/pjpeg")},
    {"content_type": "image/png", "extensions": (".png",), "formats": {"PNG"}, "aliases": ()},
    {"content_type": "image/webp", "extensions": (".webp",), "formats": {"WEBP"}, "aliases": ()},
    {"content_type": "image/heic", "extensions": (".heic",), "formats": {"HEIF"}, "aliases": ()},
    {"content_type": "image/heif", "extensions": (".heif",), "formats": {"HEIF"}, "aliases": ()},
)
ALLOWED_CONTENT_TYPES: Final[set[str]] = {spec["content_type"] for spec in FILE_TYPE_SPECS}
CONTENT_TYPE_ALIASES: Final[dict[str, str]] = {
    alias: spec["content_type"]
    for spec in FILE_TYPE_SPECS
    for alias in spec["aliases"]
}
CONTENT_TYPE_TO_FORMATS: Final[dict[str, set[str]]] = {spec["content_type"]: spec["formats"] for spec in FILE_TYPE_SPECS}
CONTENT_TYPE_TO_EXTENSIONS: Final[dict[str, set[str]]] = {spec["content_type"]: set(spec["extensions"]) for spec in FILE_TYPE_SPECS}
EXTENSION_TO_CONTENT_TYPE: Final[dict[str, str]] = {
    extension: spec["content_type"]
    for spec in FILE_TYPE_SPECS
    for extension in spec["extensions"]
}
HEIC_BRANDS: Final[set[str]] = {"heic", "heix", "hevc", "hevx", "heim", "heis"}
HEIF_BRANDS: Final[set[str]] = {"mif1", "msf1"} | HEIC_BRANDS
FACE_CASCADE = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
HOG_DESCRIPTOR = cv2.HOGDescriptor()
HOG_DESCRIPTOR.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
