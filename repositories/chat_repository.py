from typing import Optional
from models import ChatInfo
from message_storage import MessageStorage


class ChatRepository:
    def __init__(self, storage: MessageStorage):
        self.storage = storage

    def upsert(self, chat: ChatInfo) -> None:
        """Insert or update a chat record."""
        self.storage.save_chat(chat)

    def get_stats(self, chat_id: int):
        """Return aggregated stats for a chat (delegates to storage)."""
        return self.storage.get_chat_stats(chat_id)

    # Additional convenience methods can be added later (get_by_id, delete, list)
