from repositories import ChatRepository
from models import ChatInfo
from typing import Optional


class ChatService:
    def __init__(self, repo: ChatRepository):
        self.repo = repo

    def upsert_chat(
        self,
        chat_id: int,
        chat_type: str,
        title: Optional[str] = None,
        username: Optional[str] = None,
    ):
        chat = ChatInfo(
            chat_id=chat_id, chat_type=chat_type, title=title, username=username
        )
        self.repo.upsert(chat)

    def get_stats(self, chat_id: int):
        return self.repo.get_stats(chat_id)
