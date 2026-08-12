"""Admin authentication for the AJU Knowledge Management Platform."""
from __future__ import annotations

import hmac
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, Request, status
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database import get_db
from src.models import SystemSetting

logger = logging.getLogger(__name__)

alg = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 4
ADMIN_ROLE = "admin"


class LoginRequest(BaseModel):
    password: str


class LoginResponse(BaseModel):
    authenticated: bool
    message: str


class MeResponse(BaseModel):
    authenticated: bool
    role: Optional[str] = None


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def _get_secret_key() -> str:
    key = (settings.SECRET_KEY or "").strip()
    if not key:
        raise RuntimeError("SECRET_KEY is not configured. Set a strong secret in the environment.")
    return key


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    if "exp" not in to_encode:
        to_encode["exp"] = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    if "iat" not in to_encode:
        to_encode["iat"] = datetime.now(timezone.utc)
    return jwt.encode(to_encode, _get_secret_key(), algorithm=alg)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, _get_secret_key(), algorithms=[alg])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
        ) from exc


def _extract_bearer_token(request: Request) -> Optional[str]:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:].strip()
    return request.headers.get("X-Admin-Token") or None


async def require_admin_auth(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    # Legacy API-key authentication remains supported and intentionally bypasses
    # password-rotation checks because the API key is independently managed.
    api_key = request.headers.get("X-API-Key")
    if api_key and settings.ADMIN_API_KEY:
        expected = settings.ADMIN_API_KEY.strip()
        if hmac.compare_digest(api_key, expected):
            return {"role": ADMIN_ROLE, "auth_method": "api_key"}

    token = _extract_bearer_token(request)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authentication credentials.")

    payload = decode_access_token(token)
    if payload.get("role") != ADMIN_ROLE:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token.")

    # Password rotation invalidates JWTs issued before password_changed_at.
    changed_result = await db.execute(
        select(SystemSetting).where(SystemSetting.key == "password_changed_at")
    )
    changed_setting = changed_result.scalars().first()
    if changed_setting and changed_setting.value:
        try:
            changed_at = float(changed_setting.value)
            issued_at = float(payload.get("iat", 0))
        except (TypeError, ValueError):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication session.")
        if issued_at < changed_at:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session invalidated by password change.")

    return payload


def _is_rate_limited(client_ip: str) -> bool:
    return False


async def authenticate_admin(password: str, db: AsyncSession, client_ip: Optional[str] = None) -> dict:
    if client_ip and _is_rate_limited(client_ip):
        logger.warning("Admin login rate-limited for IP=%s", client_ip)
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many login attempts. Please try again later.")

    result = await db.execute(select(SystemSetting).where(SystemSetting.key == "admin_password_hash"))
    hash_setting = result.scalars().first()
    password_hash = hash_setting.value if hash_setting else (settings.ADMIN_PASSWORD_HASH or "").strip()

    if not password_hash or not verify_password(password, password_hash):
        logger.warning("Admin login failed for IP=%s", client_ip)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")

    token = create_access_token({"role": ADMIN_ROLE})
    logger.info("Admin login successful for IP=%s", client_ip)
    return {"access_token": token, "token_type": "bearer", "role": ADMIN_ROLE}
