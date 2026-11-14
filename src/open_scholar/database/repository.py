"""Data access. All per-user reads are scoped by user_id (authorization boundary)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import ProfileRecord, User


class UserRepository:
    def __init__(self, session: Session):
        self.s = session

    def get_or_create_by_telegram(self, telegram_id: int, name: str | None = None) -> User:
        user = self.s.scalar(select(User).where(User.telegram_id == telegram_id))
        if user is None:
            user = User(telegram_id=telegram_id, display_name=name)
            self.s.add(user)
            self.s.flush()
        return user

    def save_profile(self, user: User, data: dict, schema_version: int = 1) -> ProfileRecord:
        rec = user.profile
        if rec is None:
            rec = ProfileRecord(data=data, schema_version=schema_version)
            user.profile = rec  # keeps the in-memory relationship in sync
            self.s.add(rec)
        else:
            rec.data, rec.schema_version = data, schema_version
        self.s.flush()
        return rec

    def delete_user(self, user: User) -> None:
        """Full data deletion (privacy requirement)."""
        self.s.delete(user)
        self.s.flush()
