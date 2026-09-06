from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .config import get_user_settings
from .database import get_session
from .models import User
from .security import InvalidTokenError, decode_token

bearer = HTTPBearer(auto_error=False)
Session = Annotated[AsyncSession, Depends(get_session)]


async def get_current_user(
    session: Session,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication is required.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    try:
        claims = decode_token(credentials.credentials, "access", get_user_settings())
    except InvalidTokenError as exc:
        raise unauthorized from exc
    user = await session.scalar(
        select(User).options(selectinload(User.roles)).where(User.id == UUID(claims["sub"]))
    )
    if user is None or not user.is_active:
        raise unauthorized
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def require_admin(user: CurrentUser) -> User:
    if "admin" not in user.role_names:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required.")
    return user


AdminUser = Annotated[User, Depends(require_admin)]
