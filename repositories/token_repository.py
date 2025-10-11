from typing import Optional
from datetime import datetime
from message_storage import MessageStorage


class TokenRepository:
    def __init__(self, storage: MessageStorage):
        self.storage = storage

    def save(
        self,
        user_id: int,
        chat_id: int,
        tokens: int,
        role: str = "user",
        message_id: Optional[int] = None,
        timestamp: Optional[datetime] = None,
        interaction_id: Optional[str] = None,
    ) -> int:
        return self.storage.save_token_usage(
            user_id=user_id,
            chat_id=chat_id,
            tokens=tokens,
            role=role,
            message_id=message_id,
            timestamp=timestamp,
            interaction_id=interaction_id,
        )

    def user_stats(self, user_id: int):
        return self.storage.get_user_token_stats(user_id)
