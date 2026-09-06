from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import get_order_settings

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    user_id: UUID
    roles: frozenset[str]


def decode_principal(credentials: HTTPAuthorizationCredentials) -> Principal:
    settings = get_order_settings()
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
        return Principal(UUID(claims["sub"]), frozenset(claims["roles"]))
    except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A valid access token is required.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def optional_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> Principal | None:
    return decode_principal(credentials) if credentials else None


async def required_principal(
    principal: Annotated[Principal | None, Depends(optional_principal)],
) -> Principal:
    if principal is None:
        raise HTTPException(status_code=401, detail="Authentication is required.")
    return principal


async def admin_principal(
    principal: Annotated[Principal, Depends(required_principal)],
) -> Principal:
    if "admin" not in principal.roles:
        raise HTTPException(status_code=403, detail="Administrator access is required.")
    return principal


OptionalPrincipal = Annotated[Principal | None, Depends(optional_principal)]
RequiredPrincipal = Annotated[Principal, Depends(required_principal)]
AdminPrincipal = Annotated[Principal, Depends(admin_principal)]
