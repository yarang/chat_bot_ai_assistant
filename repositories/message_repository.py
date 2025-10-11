from typing import List, Optional
from models import Message
from message_storage import MessageStorage
from datetime import datetime


class MessageRepository:
    def __init__(self, storage: MessageStorage):
        self.storage = storage

    def save(self, message: Message) -> int:
        """Save a Message dataclass and return its database id."""
        return self.storage.save_message(message)

    def history(
        self,
        chat_id: int,
        user_id: Optional[int] = None,
        limit: int = 20,
        include_system: bool = True,
    ) -> List[Message]:
        return self.storage.get_conversation_history(
            chat_id=chat_id, user_id=user_id, limit=limit, include_system=include_system
        )

    def clear_conversation(self, chat_id: int, user_id: int) -> int:
        return self.storage.clear_conversation(chat_id, user_id)

    def search(
        self,
        query: str,
        chat_id: Optional[int] = None,
        user_id: Optional[int] = None,
        limit: int = 50,
    ) -> List[Message]:
        return self.storage.search_messages(
            query=query, chat_id=chat_id, user_id=user_id, limit=limit
        )

    def list_recent(self, limit: int = 50):
        with self.storage._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM messages ORDER BY timestamp DESC LIMIT ?", (limit,)
            )
            rows = cursor.fetchall()
            results = []
            for row in rows:
                results.append(dict(row))
            return results
