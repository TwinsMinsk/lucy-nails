"""TOTP MFA setup, verification, and one-time backup codes."""

import base64
import hashlib
import hmac
import secrets
from datetime import datetime
from uuid import UUID

import pyotp
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.auth_security import MfaCredential
from app.models.rbac import Role, UserRoleAssignment
from app.models.user import User


def _key_material() -> bytes:
    material = settings.MFA_ENCRYPTION_KEY or settings.JWT_SECRET_KEY
    return base64.urlsafe_b64encode(hashlib.sha256(material.encode("utf-8")).digest())


def _backup_hash(code: str) -> str:
    pepper = (settings.MFA_ENCRYPTION_KEY or settings.JWT_SECRET_KEY).encode("utf-8")
    return hmac.new(pepper, code.encode("utf-8"), hashlib.sha256).hexdigest()


class MfaService:
    @staticmethod
    async def requires_mfa(db: AsyncSession, user_id: UUID) -> bool:
        role_name = await db.scalar(
            select(Role.name)
            .join(UserRoleAssignment, UserRoleAssignment.role_id == Role.id)
            .where(
                UserRoleAssignment.user_id == user_id,
                Role.name.in_(("owner", "admin")),
            )
            .limit(1)
        )
        return role_name is not None

    @staticmethod
    async def get_credential(
        db: AsyncSession,
        user_id: UUID,
        *,
        for_update: bool = False,
    ) -> MfaCredential | None:
        query = select(MfaCredential).where(MfaCredential.user_id == user_id)
        if for_update:
            query = query.with_for_update()
        return await db.scalar(query)

    @staticmethod
    async def get_or_create_setup(
        db: AsyncSession, user: User
    ) -> tuple[MfaCredential, str, str]:
        credential = await MfaService.get_credential(db, user.id)
        if credential is not None and credential.enabled_at is not None:
            raise ValueError("MFA is already enabled")
        if credential is None:
            secret = pyotp.random_base32()
            encrypted = Fernet(_key_material()).encrypt(secret.encode("ascii")).decode("ascii")
            credential = MfaCredential(
                user_id=user.id,
                secret_encrypted=encrypted,
                backup_code_hashes=[],
            )
            db.add(credential)
            await db.flush()
        else:
            secret = MfaService.decrypt_secret(credential)
        uri = pyotp.TOTP(secret).provisioning_uri(
            name=user.email,
            issuer_name="Lucy Nails Academy",
        )
        return credential, secret, uri

    @staticmethod
    def decrypt_secret(credential: MfaCredential) -> str:
        try:
            return Fernet(_key_material()).decrypt(
                credential.secret_encrypted.encode("ascii")
            ).decode("ascii")
        except InvalidToken as exc:
            raise ValueError("MFA secret cannot be decrypted") from exc

    @staticmethod
    def enable(credential: MfaCredential, code: str) -> list[str] | None:
        secret = MfaService.decrypt_secret(credential)
        if not pyotp.TOTP(secret).verify(code.strip(), valid_window=1):
            return None
        backup_codes = [secrets.token_hex(5).upper() for _ in range(8)]
        credential.backup_code_hashes = [_backup_hash(item) for item in backup_codes]
        credential.enabled_at = datetime.utcnow()
        credential.updated_at = datetime.utcnow()
        return backup_codes

    @staticmethod
    def verify(credential: MfaCredential, code: str) -> bool:
        normalized = code.strip().replace("-", "").upper()
        if normalized.isdigit() and len(normalized) == 6:
            secret = MfaService.decrypt_secret(credential)
            return bool(pyotp.TOTP(secret).verify(normalized, valid_window=1))

        candidate = _backup_hash(normalized)
        remaining = list(credential.backup_code_hashes or [])
        for stored in remaining:
            if hmac.compare_digest(stored, candidate):
                remaining.remove(stored)
                credential.backup_code_hashes = remaining
                credential.updated_at = datetime.utcnow()
                return True
        return False
