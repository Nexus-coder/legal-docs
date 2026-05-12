from pydantic import ConfigDict, EmailStr, Field
from src.models import CustomBaseModel


class UserBase(CustomBaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserRead(UserBase):
    id: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class Token(CustomBaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(CustomBaseModel):
    email: str | None = None
