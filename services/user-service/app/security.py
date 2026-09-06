from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Any, Literal
from uuid import UUID, uuid4

import jwt
from pwdlib import PasswordHash

from .config import UserServiceSettings

password_hash = PasswordHash.recommended()


class InvalidTokenError(ValueError):
    pass


@dataclass(frozen=True)
class EncodedToken:
    value: str
    jti: UUID
    expires_at: datetime


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, encoded_hash: str) -> bool:
    return password_hash.verify(password, encoded_hash)


def hash_token(token: str) -> str:
    return sha256(token.encode()).hexdigest()


def create_token(
    user_id: UUID,
    token_type: Literal["access", "refresh"],
    settings: UserServiceSettings,
) -> EncodedToken:
    now = datetime.now(UTC)
    lifetime = (
        timedelta(minutes=settings.access_token_minutes)
        if token_type == "access"
        else timedelta(days=settings.refresh_token_days)
    )
    expires_at = now + lifetime
    jti = uuid4()
    claims = {
        "sub": str(user_id),
        "jti": str(jti),
        "type": token_type,
        "iat": now,
        "exp": expires_at,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
    }
    value = jwt.encode(claims, settings.jwt_secret_key, algorithm="HS256")
    return EncodedToken(value=value, jti=jti, expires_at=expires_at)


def decode_token(
    token: str,
    expected_type: Literal["access", "refresh"],
    settings: UserServiceSettings,
) -> dict[str, Any]:
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=["HS256"],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            options={"require": ["sub", "jti", "type", "iat", "exp"]},
        )
        if claims["type"] != expected_type:
            raise InvalidTokenError("Unexpected token type")
        UUID(claims["sub"])
        UUID(claims["jti"])
        return claims
    except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
        raise InvalidTokenError("Invalid or expired token") from exc
