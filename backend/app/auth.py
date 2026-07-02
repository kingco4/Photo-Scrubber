from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Annotated, Final, Optional, TypedDict

from fastapi import Cookie, Header, HTTPException, Request, status

from .config import (
    AUTH_COOKIE_NAME,
    AUTH_PASSWORD,
    AUTH_SECRET,
    AUTH_USERNAME,
    LOGIN_BLOCK_SECONDS,
    LOGIN_MAX_ATTEMPTS,
    TOKEN_TTL_HOURS,
    VALIDATION_SKIP_THRESHOLD,
)

class LoginAttemptState(TypedDict):
    count: int
    blocked_until: int


class TokenPayload(TypedDict):
    sub: str
    exp: int
    jti: str


REVOKED_TOKENS: dict[str, int] = {}
LOGIN_ATTEMPTS: dict[str, LoginAttemptState] = {}
IP_UPLOAD_COUNTS: dict[str, int] = {}
DEFAULT_LOGIN_ATTEMPT_STATE: Final[LoginAttemptState] = {"count": 0, "blocked_until": 0}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


@dataclass
class AuthContext:
    username: str
    token: str
    jti: str
    expires_at: int
    client_id: str


def client_identifier(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def create_access_token(username: str) -> str:
    expires_at = int((utc_now() + timedelta(hours=TOKEN_TTL_HOURS)).timestamp())
    payload: TokenPayload = {"sub": username, "exp": expires_at, "jti": secrets.token_urlsafe(12)}
    encoded_payload = b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(AUTH_SECRET.encode("utf-8"), encoded_payload.encode("ascii"), hashlib.sha256).digest()
    return f"{encoded_payload}.{b64url_encode(signature)}"


def purge_expired_revocations() -> None:
    now_ts = int(utc_now().timestamp())
    expired = [jti for jti, exp in REVOKED_TOKENS.items() if exp <= now_ts]
    for jti in expired:
        REVOKED_TOKENS.pop(jti, None)


def verify_access_token(token: str) -> tuple[str, str, int]:
    try:
        encoded_payload, encoded_signature = token.split(".", 1)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.") from exc
    expected_signature = hmac.new(AUTH_SECRET.encode("utf-8"), encoded_payload.encode("ascii"), hashlib.sha256).digest()
    actual_signature = b64url_decode(encoded_signature)
    if not hmac.compare_digest(actual_signature, expected_signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")
    try:
        payload = json.loads(b64url_decode(encoded_payload))
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.") from exc
    exp = payload.get("exp")
    sub = payload.get("sub")
    jti = payload.get("jti")
    if not isinstance(exp, int) or not isinstance(sub, str) or not isinstance(jti, str):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")
    if exp < int(utc_now().timestamp()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired.")
    purge_expired_revocations()
    if jti in REVOKED_TOKENS:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked.")
    return sub, jti, exp


def authenticate_user(username: str, password: str) -> bool:
    return hmac.compare_digest(username, AUTH_USERNAME) and hmac.compare_digest(password, AUTH_PASSWORD)


def get_current_user(
    request: Request,
    authorization: Annotated[Optional[str], Header()] = None,
    session_cookie: Annotated[Optional[str], Cookie(alias=AUTH_COOKIE_NAME)] = None,
) -> AuthContext:
    token = None
    if authorization:
        scheme, _, header_token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not header_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization header.")
        token = header_token
    elif session_cookie:
        token = session_cookie
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authentication token.")
    username, jti, expires_at = verify_access_token(token)
    return AuthContext(username, token, jti, expires_at, client_identifier(request))


def validate_login_input(username: str, password: str, access_code: str) -> tuple[str, str, str]:
    normalized_username = username.strip()
    normalized_access_code = access_code.strip()
    if not normalized_username:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Username is required.")
    if len(normalized_username) > 256:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Username must be at most 256 characters.")
    if not password:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Password is required.")
    if len(password) > 256:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Password must be at most 256 characters.")
    if len(normalized_access_code) > 64:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Access code must be at most 64 characters.")
    return normalized_username, password, normalized_access_code


def ensure_login_not_blocked(client_id: str) -> None:
    attempt_state = LOGIN_ATTEMPTS.get(client_id)
    if not attempt_state:
        return
    blocked_until = attempt_state.get("blocked_until", 0)
    if blocked_until > int(utc_now().timestamp()):
        retry_after = blocked_until - int(utc_now().timestamp())
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=f"Too many failed login attempts. Try again in {retry_after} seconds.")


def record_login_failure(client_id: str) -> None:
    now_ts = int(utc_now().timestamp())
    attempt_state = LOGIN_ATTEMPTS.get(client_id, DEFAULT_LOGIN_ATTEMPT_STATE.copy())
    if attempt_state.get("blocked_until", 0) <= now_ts:
        attempt_state["count"] = attempt_state.get("count", 0) + 1
    if attempt_state["count"] >= LOGIN_MAX_ATTEMPTS:
        attempt_state["blocked_until"] = now_ts + LOGIN_BLOCK_SECONDS
        attempt_state["count"] = 0
    LOGIN_ATTEMPTS[client_id] = attempt_state


def clear_login_failures(client_id: str) -> None:
    LOGIN_ATTEMPTS.pop(client_id, None)


def get_ip_upload_count(client_id: str) -> int:
    return IP_UPLOAD_COUNTS.get(client_id, 0)


def increment_ip_upload_count(client_id: str) -> int:
    next_count = get_ip_upload_count(client_id) + 1
    IP_UPLOAD_COUNTS[client_id] = next_count
    return next_count


def should_skip_upload_validations(current_user: AuthContext) -> bool:
    return get_ip_upload_count(current_user.client_id) >= VALIDATION_SKIP_THRESHOLD
