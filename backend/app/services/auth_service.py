"""Auth service: register, login, refresh-token rotation, logout.

Refresh rotation (PLAN.md 3.1):
- login  -> new token family
- refresh -> validate presented token; if already rotated/revoked => reuse
  attack => revoke whole family; else revoke it, issue replacement in the
  same family.
- logout -> revoke the presented token's family.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, InvalidCredentialsError, TokenError
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    refresh_token_expiry,
    verify_password,
)
from app.models import RefreshToken, User, UserSetting

UTC = timezone.utc


async def register(db: AsyncSession, email: str, password: str, display_name: str | None) -> User:
    existing = await db.scalar(select(User).where(User.email == email.lower()))
    if existing:
        raise ConflictError("Email is already registered")
    from app.core.config import get_settings as _cfg

    admins = _cfg().admin_email_list
    user = User(
        email=email.lower(),
        password_hash=hash_password(password),
        display_name=display_name,
        is_admin=("*" in admins) or (email.lower() in admins),
    )
    db.add(user)
    await db.flush()
    db.add(UserSetting(user_id=user.id))  # default settings row
    await db.commit()
    await db.refresh(user)
    return user


async def login(db: AsyncSession, email: str, password: str) -> tuple[User, str, str]:
    """Returns (user, access_token, raw_refresh_token)."""
    user = await db.scalar(
        select(User).where(User.email == email.lower(), User.is_active.is_(True))
    )
    # Same generic error whether email or password is wrong.
    if user is None or not verify_password(password, user.password_hash):
        raise InvalidCredentialsError()

    raw, token_hash = generate_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            family_id=uuid.uuid4(),
            expires_at=refresh_token_expiry(),
        )
    )
    await db.commit()
    return user, create_access_token(user.id), raw


async def refresh(db: AsyncSession, raw_refresh_token: str) -> tuple[User, str, str]:
    """Rotate refresh token. Returns (user, new_access_token, new_raw_refresh_token)."""
    token_hash = hash_refresh_token(raw_refresh_token)
    token = await db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))

    if token is None:
        raise TokenError("Invalid refresh token")

    now = datetime.now(UTC)
    if token.revoked_at is not None:
        # Reuse of a rotated token => possible theft => kill the family.
        await _revoke_family(db, token.family_id)
        await db.commit()
        raise TokenError("Refresh token reuse detected; all sessions revoked")

    expires = token.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    if expires < now:
        raise TokenError("Refresh token expired")

    user = await db.scalar(
        select(User).where(User.id == token.user_id, User.is_active.is_(True))
    )
    if user is None:
        raise TokenError("User not found or inactive")

    new_raw, new_hash = generate_refresh_token()
    replacement = RefreshToken(
        user_id=user.id,
        token_hash=new_hash,
        family_id=token.family_id,
        expires_at=refresh_token_expiry(),
    )
    db.add(replacement)
    await db.flush()
    token.revoked_at = now
    token.replaced_by = replacement.id
    await db.commit()
    return user, create_access_token(user.id), new_raw


async def logout(db: AsyncSession, raw_refresh_token: str) -> None:
    token_hash = hash_refresh_token(raw_refresh_token)
    token = await db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    if token is not None:
        await _revoke_family(db, token.family_id)
        await db.commit()


async def _revoke_family(db: AsyncSession, family_id: uuid.UUID) -> None:
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
