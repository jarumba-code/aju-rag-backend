"""
Admin authentication module for the AJU Knowledge Management Platform.

Provides:
 - Password hashing / verification using bcrypt.
 - JWT-based admin session tokens.
 - FastAPI dependencies for protecting admin routes.

Password policy:
 - The production password is NEVER stored in plaintext.
 - Only ``ADMIN_PASSWORD_HASH`` (a bcrypt hash) is stored in the environment.
 - Passwords are never logged or returned in API responses.

Session policy:
 - Admin sessions are represented by short-lived JWT bearer tokens.
 - The frontend should store these in an HttpOnly, Secure, SameSite cookie
   rather than localStorage to reduce XSS risk.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database import get_db
from src.models import SystemSetting

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

alg = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 4  # 4 hours
ADMIN_ROLE = "admin"

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    password: str


class LoginResponse(BaseModel):
    authenticated: bool
    message: str


class MeResponse(BaseModel):
    authenticated: bool
    role: Optional[str] = None


# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False

# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def _get_secret_key() -> str:
    key = (settings.SECRET_KEY or "").strip()
    if not key:
        raise RuntimeError(
            "SECRET_KEY is not configured. Set a strong secret in the environment."
        )
    return key


def create_access_token(data: dict) -> str:
    """
    Create a JWT access token.

    Honors an existing ``exp`` / ``iat`` in *data* if supplied (useful for
    tests). Otherwise applies the default expiration window.
    """
    secret = _get_secret_key()
    to_encode = data.copy()
    if "exp" not in to_encode:
        to_encode["exp"] = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    if "iat" not in to_encode:
        to_encode["iat"] = datetime.now(timezone.utc)
    return jwt.encode(to_encode, secret, algorithm=alg)


def decode_access_token(token: str) -> dict:
    secret = _get_secret_key()
    try:
        payload = jwt.decode(token, secret, algorithms=[alg])
        return payload
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
        ) from exc

# ---------------------------------------------------------------------------
# Authentication dependencies
# ---------------------------------------------------------------------------

# Declared OpenAPI security scheme (shown in Swagger UI's "Authorize" dialog).
# auto_error=False keeps the legacy X-API-Key fallback working: when the
# Authorization header is absent, ``credentials`` is simply None and
# ``require_admin_auth`` raises its own 401. Authenticated flow is unchanged.
bearer_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="BearerAuth",
    description=(
        "Admin bearer token. Obtain one via POST /api/v1/admin/auth/login, "
        "then click Authorize and paste the returned access_token. "
        "Sent as: Authorization: Bearer <token>"
    ),
)


def _extract_bearer_token(request: Request) -> Optional[str]:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:].strip()
    return request.headers.get("X-Admin-Token") or None


async def require_admin_auth(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> dict:
    api_key = request.headers.get("X-API-Key")
    if api_key and settings.ADMIN_API_KEY:
        expected = settings.ADMIN_API_KEY.strip()
        if hmac.compare_digest(api_key, expected):
            return {"role": ADMIN_ROLE, "auth_method": "api_key"}

    token = _extract_bearer_token(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials.",
        )

    payload = decode_access_token(token)
    role = payload.get("role")
    if role != ADMIN_ROLE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
        )

    # --- Session invalidation on password change ---
    # If the admin password has been rotated since this token was issued,
    # the token's iat is older than password_changed_at and must be rejected.
    # The X-API-Key path above intentionally bypasses this (keys are rotated
    # out-of-band via configuration).
    try:
        result = await db.execute(
            select(SystemSetting).where(SystemSetting.key == "password_changed_at")
        )
        setting = result.scalars().first()
        if setting and setting.value:
            try:
                changed_at = float(setting.value)
            except (TypeError, ValueError):
                changed_at = None
            if changed_at is not None:
                issued = payload.get("iat")
                if issued is not None and float(issued) < changed_at:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Session invalidated by password change.",
                    )
    except HTTPException:
        raise
    except Exception:
        logger.debug("password_changed_at revocation check unavailable", exc_info=True)

    return payload


# ---------------------------------------------------------------------------
# Rate-limiting hooks
# ---------------------------------------------------------------------------

def _is_rate_limited(client_ip: str) -> bool:
    return False


# ---------------------------------------------------------------------------
# Core login logic
# ---------------------------------------------------------------------------

async def authenticate_admin(password: str, db: AsyncSession, client_ip: Optional[str] = None) -> dict:
    if client_ip and _is_rate_limited(client_ip):
        logger.warning("Admin login rate-limited for IP=%s", client_ip)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
        )

    result = await db.execute(select(SystemSetting).where(SystemSetting.key == "admin_password_hash"))
    hash_setting = result.scalars().first()

    if hash_setting:
        password_hash = hash_setting.value
    else:
        password_hash = (settings.ADMIN_PASSWORD_HASH or "").strip()

    if not password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
        )

    if not verify_password(password, password_hash):
        logger.warning("Admin login failed for IP=%s", client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
        )

    token = create_access_token({"role": ADMIN_ROLE})
    logger.info("Admin login successful for IP=%s", client_ip)
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": ADMIN_ROLE,
    }
