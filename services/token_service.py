from repositories import TokenRepository
from typing import Optional
from datetime import datetime


class TokenService:
    def __init__(self, repo: TokenRepository):
        self.repo = repo

    def record_tokens(
        self,
        user_id: int,
        chat_id: int,
        tokens: int,
        role: str = "user",
        message_id: Optional[int] = None,
        interaction_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ):
        return self.repo.save(
            user_id=user_id,
            chat_id=chat_id,
            tokens=tokens,
            role=role,
            message_id=message_id,
            interaction_id=interaction_id,
            timestamp=timestamp,
        )

    def user_stats(self, user_id: int):
        return self.repo.user_stats(user_id)
