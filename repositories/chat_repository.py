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

    def update_persona(self, chat_id: int, persona_prompt: str) -> None:
        """Update the persona for a specific chat."""
        self.storage.update_chat_persona(chat_id, persona_prompt)

    def get_persona(self, chat_id: int) -> Optional[str]:
        """Get the persona for a specific chat."""
        return self.storage.get_chat_persona(chat_id)

    # Additional convenience methods can be added later (get_by_id, delete, list)
