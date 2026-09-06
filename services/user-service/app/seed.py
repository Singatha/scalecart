import asyncio
import os

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .database import session_factory
from .models import Role, User
from .schemas import RegistrationRequest
from .security import hash_password


async def seed_admin() -> None:
    email = os.getenv("BOOTSTRAP_ADMIN_EMAIL")
    password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD")
    if not email or not password:
        raise SystemExit("Set BOOTSTRAP_ADMIN_EMAIL and BOOTSTRAP_ADMIN_PASSWORD before seeding.")
    if session_factory is None:
        raise SystemExit("DATABASE_URL is required before seeding.")

    payload = RegistrationRequest(
        email=email,
        password=password,
        first_name=os.getenv("BOOTSTRAP_ADMIN_FIRST_NAME", "Store"),
        last_name=os.getenv("BOOTSTRAP_ADMIN_LAST_NAME", "Administrator"),
    )
    normalized_email = str(payload.email).lower()
    async with session_factory() as session:
        roles = list(
            await session.scalars(select(Role).where(Role.name.in_(["admin", "customer"])))
        )
        if {role.name for role in roles} != {"admin", "customer"}:
            raise SystemExit("Run the user-service migrations before seeding.")
        user = await session.scalar(
            select(User).options(selectinload(User.roles)).where(User.email == normalized_email)
        )
        if user is None:
            user = User(
                email=normalized_email,
                password_hash=hash_password(payload.password),
                first_name=payload.first_name,
                last_name=payload.last_name,
                roles=roles,
            )
            session.add(user)
            action = "created"
        else:
            current_roles = {role.name for role in user.roles}
            user.roles.extend(role for role in roles if role.name not in current_roles)
            action = "updated"
        await session.commit()
    print(f"Bootstrap administrator {normalized_email} {action}.")


if __name__ == "__main__":
    asyncio.run(seed_admin())
