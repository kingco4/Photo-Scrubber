from __future__ import annotations

import asyncio
import hmac
import time
from typing import Annotated, Awaitable, Callable, TypedDict

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, Response as FastAPIResponse, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from .auth import AuthContext, REVOKED_TOKENS, authenticate_user, clear_login_failures, client_identifier, create_access_token, ensure_login_not_blocked, get_current_user, get_ip_upload_count, increment_ip_upload_count, record_login_failure, should_skip_upload_validations, validate_login_input
from .config import AUTH_ACCESS_CODE, AUTH_COOKIE_NAME, AUTH_COOKIE_SECURE, LIVE_FRAME_JPEG_QUALITY, LIVE_FRAME_MAX_DIMENSION, LOG_LEVEL, TOKEN_TTL_HOURS, VALIDATION_SKIP_THRESHOLD, logger, register_heif_opener
from .image_ops import Options, bgr_to_jpeg_bytes, bgr_to_png_bytes, pil_to_bgr, process_image, resize_long_edge, scrub_people, scrub_text
from .uploads import read_and_validate_upload


class HealthResponse(TypedDict):
    ok: bool


class SettingsResponse(TypedDict):
    requires_access_code: bool


class AuthStatusResponse(TypedDict):
    username: str
    ip_upload_count: int
    skip_upload_validations: bool


class LoginResponse(AuthStatusResponse):
    expires_in: int


class LogoutResponse(TypedDict):
    ok: bool

app = FastAPI(title="Scubber API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
if register_heif_opener is not None:
    register_heif_opener()


def validate_processing_options(blur_people: bool, remove_text: bool) -> None:
    if not blur_people and not remove_text:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="At least one processing option must be enabled.")


async def process_image_async(pil, opts: Options) -> bytes:
    return await asyncio.to_thread(lambda: bgr_to_png_bytes(process_image(pil, opts)))


def build_live_frame(pil, opts: Options, constrained_dimension: int, jpeg_quality: int) -> bytes:
    bgr = resize_long_edge(pil_to_bgr(pil), constrained_dimension)
    if opts.remove_text:
        bgr = scrub_text(bgr)
    if opts.blur_people:
        bgr = scrub_people(bgr, blur_strength=opts.blur_strength, detect_bodies=opts.detect_bodies)
    return bgr_to_jpeg_bytes(bgr, jpeg_quality)


async def build_live_frame_async(pil, opts: Options, constrained_dimension: int, jpeg_quality: int) -> bytes:
    return await asyncio.to_thread(build_live_frame, pil, opts, constrained_dimension, jpeg_quality)


@app.on_event("startup")
async def log_startup() -> None:
    logger.info("Starting Photo Scrubber API", extra={"log_level": LOG_LEVEL, "heif_enabled": register_heif_opener is not None})


@app.middleware("http")
async def log_requests(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    started = time.perf_counter()
    client_host = request.client.host if request.client else "unknown"
    logger.info("Request started %s %s from %s", request.method, request.url.path, client_host)
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = (time.perf_counter() - started) * 1000
        logger.exception("Request failed %s %s in %.2fms", request.method, request.url.path, duration_ms)
        raise
    duration_ms = (time.perf_counter() - started) * 1000
    logger.info("Request completed %s %s -> %s in %.2fms", request.method, request.url.path, response.status_code, duration_ms)
    return response


@app.get("/health")
def health() -> HealthResponse:
    return {"ok": True}


@app.get("/auth/settings")
def auth_settings() -> SettingsResponse:
    return {"requires_access_code": bool(AUTH_ACCESS_CODE)}


@app.post("/auth/login")
async def login(
    response: FastAPIResponse,
    request: Request,
    username: Annotated[str, Form(min_length=1, max_length=256)],
    password: Annotated[str, Form(min_length=1, max_length=256)],
    access_code: Annotated[str, Form(max_length=64)] = "",
) -> LoginResponse:
    client_id = client_identifier(request)
    ensure_login_not_blocked(client_id)
    username, password, access_code = validate_login_input(username, password, access_code)
    if AUTH_ACCESS_CODE and not hmac.compare_digest(access_code, AUTH_ACCESS_CODE):
        record_login_failure(client_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access code.")
    if not authenticate_user(username, password):
        record_login_failure(client_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password.")
    clear_login_failures(client_id)
    token = create_access_token(username)
    response.set_cookie(key=AUTH_COOKIE_NAME, value=token, max_age=TOKEN_TTL_HOURS * 60 * 60, httponly=True, secure=AUTH_COOKIE_SECURE, samesite="lax", path="/")
    count = get_ip_upload_count(client_id)
    return {"username": username, "expires_in": TOKEN_TTL_HOURS * 60 * 60, "ip_upload_count": count, "skip_upload_validations": count >= VALIDATION_SKIP_THRESHOLD}


@app.get("/auth/me")
def auth_me(current_user: AuthContext = Depends(get_current_user)) -> AuthStatusResponse:
    return {"username": current_user.username, "ip_upload_count": get_ip_upload_count(current_user.client_id), "skip_upload_validations": should_skip_upload_validations(current_user)}


@app.post("/auth/logout")
def auth_logout(response: FastAPIResponse, current_user: AuthContext = Depends(get_current_user)) -> LogoutResponse:
    REVOKED_TOKENS[current_user.jti] = current_user.expires_at
    response.delete_cookie(key=AUTH_COOKIE_NAME, path="/", samesite="lax")
    return {"ok": True}


@app.post("/process")
async def process(
    file: UploadFile = File(...),
    blur_people: bool = Form(True),
    remove_text: bool = Form(True),
    blur_strength: Annotated[int, Form(ge=3, le=151)] = 31,
    detect_bodies: bool = Form(False),
    current_user: AuthContext = Depends(get_current_user),
) -> Response:
    validate_processing_options(bool(blur_people), bool(remove_text))
    pil = await read_and_validate_upload(file, skip_non_critical_checks=should_skip_upload_validations(current_user))
    png = await process_image_async(pil, Options(bool(blur_people), bool(remove_text), blur_strength, bool(detect_bodies)))
    count = increment_ip_upload_count(current_user.client_id)
    return Response(content=png, media_type="image/png", headers={"X-IP-Upload-Count": str(count), "X-Skip-Upload-Validations": "true" if count >= VALIDATION_SKIP_THRESHOLD else "false"})


@app.post("/process/live")
async def process_live(
    file: UploadFile = File(...),
    blur_people: bool = Form(True),
    remove_text: bool = Form(True),
    blur_strength: Annotated[int, Form(ge=3, le=151)] = 31,
    detect_bodies: bool = Form(False),
    max_dimension: Annotated[int, Form(ge=160, le=1920)] = 960,
    jpeg_quality: Annotated[int, Form(ge=40, le=95)] = LIVE_FRAME_JPEG_QUALITY,
    current_user: AuthContext = Depends(get_current_user),
) -> Response:
    validate_processing_options(bool(blur_people), bool(remove_text))
    pil = await read_and_validate_upload(file, skip_non_critical_checks=should_skip_upload_validations(current_user))
    opts = Options(bool(blur_people), bool(remove_text), blur_strength, bool(detect_bodies))
    constrained_dimension = min(max_dimension, LIVE_FRAME_MAX_DIMENSION)
    jpeg = await build_live_frame_async(pil, opts, constrained_dimension, jpeg_quality)
    return Response(content=jpeg, media_type="image/jpeg", headers={"Cache-Control": "no-store", "X-Photo-Scrubber-Live-Max-Dimension": str(constrained_dimension)})
