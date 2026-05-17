from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

import logging
_log = logging.getLogger(__name__)
if len(settings.SECRET_KEY) < 32:
    _log.warning(
        "SECRET_KEY is too short (%d chars). Use at least 32 characters for HS256.",
        len(settings.SECRET_KEY),
    )

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(user_id: UUID, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {
            "sub": str(user_id),
            "role": role,
            "type": ACCESS_TOKEN_TYPE,
            "exp": expire,
        },
        settings.SECRET_KEY,
        algorithm="HS256",
    )


def create_refresh_token(user_id: UUID, token_id: UUID) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return jwt.encode(
        {
            "sub": str(user_id),
            "jti": str(token_id),
            "type": REFRESH_TOKEN_TYPE,
            "exp": expire,
        },
        settings.SECRET_KEY,
        algorithm="HS256",
    )


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except JWTError:
        return None
