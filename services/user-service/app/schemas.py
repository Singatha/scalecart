from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

Name = Annotated[str, Field(min_length=1, max_length=100)]


class RegistrationRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    first_name: Name
    last_name: Name

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        checks = (
            any(c.islower() for c in value),
            any(c.isupper() for c in value),
            any(c.isdigit() for c in value),
        )
        if not all(checks):
            raise ValueError("Password must contain uppercase, lowercase, and numeric characters.")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    first_name: str
    last_name: str
    phone: str | None
    is_active: bool
    roles: list[str] = Field(validation_alias="role_names")
    created_at: datetime
    updated_at: datetime


class AuthenticationResponse(TokenPair):
    user: UserRead


class ProfileUpdate(BaseModel):
    first_name: Name | None = None
    last_name: Name | None = None
    phone: str | None = Field(default=None, max_length=32)

    @field_validator("phone")
    @classmethod
    def empty_phone_is_none(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class AddressFields(BaseModel):
    label: str = Field(min_length=1, max_length=50)
    recipient_name: str = Field(min_length=1, max_length=200)
    line1: str = Field(min_length=1, max_length=200)
    line2: str | None = Field(default=None, max_length=200)
    city: str = Field(min_length=1, max_length=100)
    region: str = Field(min_length=1, max_length=100)
    postal_code: str = Field(min_length=1, max_length=32)
    country_code: str = Field(min_length=2, max_length=2)
    phone: str | None = Field(default=None, max_length=32)
    is_default: bool = False

    @field_validator("country_code")
    @classmethod
    def normalize_country_code(cls, value: str) -> str:
        return value.upper()


class AddressCreate(AddressFields):
    pass


class AddressUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=50)
    recipient_name: str | None = Field(default=None, min_length=1, max_length=200)
    line1: str | None = Field(default=None, min_length=1, max_length=200)
    line2: str | None = Field(default=None, max_length=200)
    city: str | None = Field(default=None, min_length=1, max_length=100)
    region: str | None = Field(default=None, min_length=1, max_length=100)
    postal_code: str | None = Field(default=None, min_length=1, max_length=32)
    country_code: str | None = Field(default=None, min_length=2, max_length=2)
    phone: str | None = Field(default=None, max_length=32)
    is_default: bool | None = None

    @field_validator("country_code")
    @classmethod
    def normalize_country_code(cls, value: str | None) -> str | None:
        return value.upper() if value else value


class AddressRead(AddressFields):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class RoleAssignment(BaseModel):
    roles: list[str] = Field(min_length=1)

    @field_validator("roles")
    @classmethod
    def normalize_roles(cls, value: list[str]) -> list[str]:
        normalized = sorted({role.strip().lower() for role in value if role.strip()})
        if not normalized:
            raise ValueError("At least one role is required.")
        return normalized
