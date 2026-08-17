from pydantic import BaseModel, EmailStr, Field, field_validator


def _bcrypt_password(value: str) -> str:
    if len(value.encode("utf-8")) > 72:
        raise ValueError("Password must be at most 72 UTF-8 bytes")
    return value


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=72)

    _password_bytes = field_validator("password")(_bcrypt_password)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)

    _password_bytes = field_validator("password")(_bcrypt_password)


class DeleteAccountRequest(BaseModel):
    """Require the current password before permanently removing an account."""

    password: str = Field(min_length=1, max_length=72)

    _password_bytes = field_validator("password")(_bcrypt_password)


class Token(BaseModel):
    access_token: str
    token_type: str


class LoginResponse(BaseModel):
    message: str
    data: Token
