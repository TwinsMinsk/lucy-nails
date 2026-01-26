"""
Pydantic схемы для аутентификации.
"""

from uuid import UUID
from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    """Схема регистрации пользователя."""
    
    email: EmailStr = Field(..., description="Email пользователя")
    password: str = Field(..., min_length=6, description="Пароль (минимум 6 символов)")


class UserLogin(BaseModel):
    """Схема входа пользователя."""
    
    email: EmailStr = Field(..., description="Email пользователя")
    password: str = Field(..., description="Пароль")


class Token(BaseModel):
    """Схема JWT токенов."""
    
    access_token: str = Field(..., description="JWT access токен")
    refresh_token: str = Field(..., description="JWT refresh токен")
    token_type: str = Field(default="bearer", description="Тип токена")


class UserResponse(BaseModel):
    """Схема ответа с данными пользователя."""
    
    id: UUID = Field(..., description="UUID пользователя")
    email: str = Field(..., description="Email")
    role: str = Field(..., description="Роль (student/admin)")
    telegram_id: int | None = Field(None, description="Telegram ID")
    
    class Config:
        from_attributes = True
        use_enum_values = True
