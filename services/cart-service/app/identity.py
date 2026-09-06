from dataclasses import dataclass
from typing import Annotated
from uuid import UUID, uuid4

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import get_cart_settings

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CartIdentity:
    key: str
    cart_id: UUID | None
    user_id: UUID | None


def decode_user_id(credentials: HTTPAuthorizationCredentials) -> UUID:
    settings = get_cart_settings()
    try:
        claims = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=["HS256"],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            options={"require": ["sub", "type", "iat", "exp"]},
        )
        if claims["type"] != "access":
            raise ValueError("Unexpected token type")
        return UUID(claims["sub"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A valid access token is required.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def resolve_cart_identity(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    guest_cart_id: Annotated[UUID | None, Header(alias="X-Cart-ID")] = None,
) -> CartIdentity:
    if credentials is not None:
        user_id = decode_user_id(credentials)
        return CartIdentity(key=f"cart:user:{user_id}", cart_id=None, user_id=user_id)
    cart_id = guest_cart_id or uuid4()
    return CartIdentity(key=f"cart:guest:{cart_id}", cart_id=cart_id, user_id=None)


Identity = Annotated[CartIdentity, Depends(resolve_cart_identity)]
