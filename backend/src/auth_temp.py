async def require_admin_auth(request: Request) -> dict:
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

    # Password-rotation invalidation requires a DB session.
    # We acquire it lazily so API-key auth never touches the database.
    try:
        from src.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(SystemSetting).where(SystemSetting.key == "password_changed_at")
            )
            changed_at_setting = result.scalars().first()
            if changed_at_setting:
                try:
                    changed_at_ts = float(changed_at_setting.value)
                    token_iat = payload.get("iat", 0)
                    if token_iat < changed_at_ts:
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Session expired due to password change. Please log in again.",
                        )
                except ValueError:
                    pass
    except Exception:
        # If the database is unreachable, fail closed for JWT auth.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service temporarily unavailable.",
        )

    return payload
