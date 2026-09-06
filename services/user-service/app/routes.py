from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from .config import get_user_settings
from .dependencies import AdminUser, CurrentUser, Session
from .models import Address, RefreshToken, Role, User
from .schemas import (
    AddressCreate,
    AddressRead,
    AddressUpdate,
    AuthenticationResponse,
    LoginRequest,
    ProfileUpdate,
    RefreshRequest,
    RegistrationRequest,
    RoleAssignment,
    TokenPair,
    UserRead,
)
from .security import (
    InvalidTokenError,
    create_token,
    decode_token,
    hash_password,
    hash_token,
    verify_password,
)

auth_router = APIRouter(prefix="/auth", tags=["authentication"])
users_router = APIRouter(prefix="/users", tags=["users"])
settings = get_user_settings()


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _invalid_credentials() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _invalid_refresh_token() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid, expired, or already-used refresh token.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _issue_token_pair(user: User, session: Session) -> tuple[TokenPair, RefreshToken]:
    access = create_token(user.id, "access", settings, roles=user.role_names)
    refresh = create_token(user.id, "refresh", settings)
    stored_refresh = RefreshToken(
        user_id=user.id,
        jti=refresh.jti,
        token_hash=hash_token(refresh.value),
        expires_at=refresh.expires_at,
    )
    session.add(stored_refresh)
    return (
        TokenPair(
            access_token=access.value,
            refresh_token=refresh.value,
            expires_in=settings.access_token_minutes * 60,
        ),
        stored_refresh,
    )


@auth_router.post(
    "/register", response_model=AuthenticationResponse, status_code=status.HTTP_201_CREATED
)
async def register(payload: RegistrationRequest, session: Session) -> AuthenticationResponse:
    email = _normalize_email(str(payload.email))
    if await session.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email is already registered."
        )
    customer_role = await session.scalar(select(Role).where(Role.name == "customer"))
    if customer_role is None:
        raise HTTPException(status_code=503, detail="User roles have not been initialized.")

    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        first_name=payload.first_name.strip(),
        last_name=payload.last_name.strip(),
        roles=[customer_role],
    )
    session.add(user)
    try:
        await session.flush()
        tokens, _ = _issue_token_pair(user, session)
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email is already registered."
        ) from exc
    return AuthenticationResponse(user=UserRead.model_validate(user), **tokens.model_dump())


@auth_router.post("/login", response_model=AuthenticationResponse)
async def login(payload: LoginRequest, session: Session) -> AuthenticationResponse:
    user = await session.scalar(
        select(User)
        .options(selectinload(User.roles))
        .where(User.email == _normalize_email(str(payload.email)))
    )
    valid_password = user is not None and verify_password(payload.password, user.password_hash)
    if user is None or not user.is_active or not valid_password:
        raise _invalid_credentials()
    tokens, _ = _issue_token_pair(user, session)
    await session.commit()
    return AuthenticationResponse(user=UserRead.model_validate(user), **tokens.model_dump())


@auth_router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshRequest, session: Session) -> TokenPair:
    try:
        claims = decode_token(payload.refresh_token, "refresh", settings)
    except InvalidTokenError as exc:
        raise _invalid_refresh_token() from exc

    now = datetime.now(UTC)
    stored = await session.scalar(
        select(RefreshToken)
        .options(selectinload(RefreshToken.user).selectinload(User.roles))
        .where(
            RefreshToken.jti == UUID(claims["jti"]),
            RefreshToken.token_hash == hash_token(payload.refresh_token),
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > now,
        )
        .with_for_update()
    )
    if stored is None or not stored.user.is_active:
        await session.rollback()
        raise _invalid_refresh_token()

    stored.revoked_at = now
    tokens, replacement = _issue_token_pair(stored.user, session)
    stored.replaced_by_jti = replacement.jti
    await session.commit()
    return tokens


@auth_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(payload: RefreshRequest, session: Session) -> Response:
    try:
        claims = decode_token(payload.refresh_token, "refresh", settings)
    except InvalidTokenError as exc:
        raise _invalid_refresh_token() from exc
    stored = await session.scalar(
        select(RefreshToken).where(
            RefreshToken.jti == UUID(claims["jti"]),
            RefreshToken.token_hash == hash_token(payload.refresh_token),
        )
    )
    if stored is not None and stored.revoked_at is None:
        stored.revoked_at = datetime.now(UTC)
        await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@users_router.get("/me", response_model=UserRead)
async def get_profile(user: CurrentUser) -> User:
    return user


@users_router.patch("/me", response_model=UserRead)
async def update_profile(payload: ProfileUpdate, user: CurrentUser, session: Session) -> User:
    changes = payload.model_dump(exclude_unset=True)
    for name, value in changes.items():
        setattr(user, name, value.strip() if isinstance(value, str) else value)
    await session.commit()
    await session.refresh(user)
    return user


@users_router.get("/me/addresses", response_model=list[AddressRead])
async def list_addresses(user: CurrentUser, session: Session) -> list[Address]:
    result = await session.scalars(
        select(Address)
        .where(Address.user_id == user.id)
        .order_by(Address.is_default.desc(), Address.created_at.asc())
    )
    return list(result)


async def _clear_default_address(session: Session, user_id: UUID) -> None:
    await session.execute(
        update(Address).where(Address.user_id == user_id).values(is_default=False)
    )


@users_router.post("/me/addresses", response_model=AddressRead, status_code=status.HTTP_201_CREATED)
async def create_address(payload: AddressCreate, user: CurrentUser, session: Session) -> Address:
    address_count = await session.scalar(
        select(func.count()).select_from(Address).where(Address.user_id == user.id)
    )
    values = payload.model_dump()
    values["is_default"] = payload.is_default or address_count == 0
    if values["is_default"]:
        await _clear_default_address(session, user.id)
    address = Address(user_id=user.id, **values)
    session.add(address)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An address with this label already exists.",
        ) from exc
    await session.refresh(address)
    return address


async def _owned_address(address_id: UUID, user: User, session: Session) -> Address:
    address = await session.scalar(
        select(Address).where(Address.id == address_id, Address.user_id == user.id)
    )
    if address is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found.")
    return address


@users_router.patch("/me/addresses/{address_id}", response_model=AddressRead)
async def update_address(
    address_id: UUID, payload: AddressUpdate, user: CurrentUser, session: Session
) -> Address:
    address = await _owned_address(address_id, user, session)
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("is_default"):
        await _clear_default_address(session, user.id)
    for name, value in changes.items():
        setattr(address, name, value)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An address with this label already exists.",
        ) from exc
    await session.refresh(address)
    return address


@users_router.delete("/me/addresses/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_address(address_id: UUID, user: CurrentUser, session: Session) -> Response:
    address = await _owned_address(address_id, user, session)
    was_default = address.is_default
    await session.delete(address)
    await session.flush()
    if was_default:
        replacement = await session.scalar(
            select(Address)
            .where(Address.user_id == user.id)
            .order_by(Address.created_at.asc())
            .limit(1)
        )
        if replacement is not None:
            replacement.is_default = True
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@users_router.get("/{user_id}", response_model=UserRead)
async def get_user(user_id: UUID, _: AdminUser, session: Session) -> User:
    user = await session.scalar(
        select(User).options(selectinload(User.roles)).where(User.id == user_id)
    )
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return user


@users_router.put("/{user_id}/roles", response_model=UserRead)
async def assign_roles(
    user_id: UUID, payload: RoleAssignment, _: AdminUser, session: Session
) -> User:
    user = await session.scalar(
        select(User).options(selectinload(User.roles)).where(User.id == user_id)
    )
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    roles = list(await session.scalars(select(Role).where(Role.name.in_(payload.roles))))
    if len(roles) != len(payload.roles):
        found = {role.name for role in roles}
        missing = sorted(set(payload.roles) - found)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Unknown roles: {', '.join(missing)}.",
        )
    user.roles = roles
    await session.commit()
    return user
