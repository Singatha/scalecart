from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import get_product_settings

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    user_id: UUID
    roles: frozenset[str]


async def require_admin(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> Principal:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="A valid administrator access token is required.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    settings = get_product_settings()
    try:
        claims = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=["HS256"],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            options={"require": ["sub", "type", "roles", "iat", "exp"]},
        )
        if claims["type"] != "access":
            raise ValueError("Unexpected token type")
        principal = Principal(user_id=UUID(claims["sub"]), roles=frozenset(claims["roles"]))
    except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
        raise unauthorized from exc
    if "admin" not in principal.roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required.")
    return principal


AdminPrincipal = Annotated[Principal, Depends(require_admin)]
