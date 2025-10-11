from typing import Optional
from models import UserInfo
from message_storage import MessageStorage


class UserRepository:
    def __init__(self, storage: MessageStorage):
        self.storage = storage

    def upsert(self, user: UserInfo) -> None:
        """Insert or update a user record."""
        self.storage.save_user(user)

    def get_stats(self, user_id: int):
        """Return aggregated stats for a user (delegates to storage)."""
        return self.storage.get_user_stats(user_id)

    # Additional convenience methods can be added later (get_by_id, delete, list)
