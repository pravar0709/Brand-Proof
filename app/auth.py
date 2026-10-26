"""Demo authentication: signed tokens with itsdangerous, role guards."""

import os
from typing import Optional
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

SECRET_KEY = os.environ.get("SECRET_KEY", "brandproof-dev-secret-change-me")
TOKEN_MAX_AGE = 86400 * 7  # 7 days

serializer = URLSafeTimedSerializer(SECRET_KEY)
security = HTTPBearer(auto_error=False)


def create_token(user_id: int, role: str, name: str) -> str:
    """Create a signed demo token."""
    return serializer.dumps({"user_id": user_id, "role": role, "name": name})


def decode_token(token: str) -> Optional[dict]:
    """Decode and verify a signed token. Returns payload or None."""
    try:
        return serializer.loads(token, max_age=TOKEN_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """FastAPI dependency: extract and validate the current user from Bearer token."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload


def require_role(*allowed_roles: str):
    """Factory: returns a dependency that checks the user has one of the allowed roles."""
    async def role_guard(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Role '{user['role']}' not allowed. Required: {', '.join(allowed_roles)}"
            )
        return user
    return role_guard
