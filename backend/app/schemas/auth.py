"""
Pydantic схемы для аутентификации.
"""

from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    """Схема регистрации пользователя."""
    
    email: EmailStr = Field(..., description="Email пользователя")
    password: str = Field(..., min_length=6, description="Пароль (минимум 6 символов)")


class UserLogin(BaseModel):
    """Схема входа пользователя."""
    
    email: EmailStr = Field(..., description="Email пользователя")
    password: str = Field(..., description="Пароль")


class ChangePasswordRequest(BaseModel):
    """Смена пароля залогиненным пользователем."""

    current_password: str = Field(..., description="Текущий пароль")
    new_password: str = Field(..., min_length=6, description="Новый пароль (минимум 6 символов)")


class ForgotPasswordRequest(BaseModel):
    """Запрос ссылки на сброс пароля."""

    email: EmailStr = Field(..., description="Email аккаунта")


class ResetPasswordRequest(BaseModel):
    """Установка нового пароля по токену из письма."""

    token: str = Field(..., min_length=10, description="Токен из письма")
    new_password: str = Field(..., min_length=6, description="Новый пароль (минимум 6 символов)")


class Token(BaseModel):
    """Схема JWT токенов."""
    
    access_token: str = Field(..., description="JWT access токен")
    refresh_token: str = Field(..., description="JWT refresh токен")
    token_type: str = Field(default="bearer", description="Тип токена")


class UserResponse(BaseModel):
    """Схема ответа с данными пользователя."""

    id: UUID = Field(..., description="UUID пользователя")
    email: str = Field(..., description="Email")
    phone: str | None = Field(None, description="Телефон (если указан)")
    full_name: str | None = Field(None, description="ФИО (если указано)")
    role: str = Field(..., description="Роль (student/admin)")
    telegram_id: int | None = Field(None, description="Telegram ID")
    created_at: datetime = Field(..., description="Дата регистрации")
    
    class Config:
        from_attributes = True
        use_enum_values = True
