from message_storage import MessageStorage
from typing import Optional


class MessageService:
    def __init__(self, storage: MessageStorage):
        self.storage = storage

    def save_message(
        self,
        chat_id: int,
        user_id: int,
        role: str,
        content: str,
        metadata: Optional[dict] = None,
    ) -> int:
        # 메시지 저장 비즈니스 로직 (예: 전처리, 검증 등)
        cleaned_content = content.strip()
        from message_storage import Message
        from datetime import datetime

        message = Message(
            chat_id=chat_id,
            user_id=user_id,
            role=role,
            content=cleaned_content,
            timestamp=datetime.now(),
            metadata=metadata,
        )
        return self.storage.save_message(message)

    def get_history(
        self,
        chat_id: int,
        user_id: "Optional[int]" = None,
        limit: int = 20,
        include_system: bool = True,
    ):
        # 대화 이력 비즈니스 로직 (예: 필터링, 가공 등)
        return self.storage.get_conversation_history(
            chat_id=chat_id, user_id=user_id, limit=limit, include_system=include_system
        )

    def get_all_messages(self, limit: int = 20):
        """
        전체 메시지를 최신순으로 limit만큼 반환
        """
        with self.storage._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM messages ORDER BY timestamp DESC LIMIT ?", (limit,)
            )
            rows = cursor.fetchall()
            messages = []
            for row in rows:
                messages.append(
                    {
                        "chat_id": row["chat_id"],
                        "user_id": row["user_id"],
                        "role": row["role"],
                        "content": row["content"],
                        "timestamp": row["timestamp"],
                    }
                )
            return messages
    def get_user_token_stats(self, user_id: int):
        """사용자별 토큰 사용량 통계 반환"""
        return self.storage.get_user_token_stats(user_id)
        