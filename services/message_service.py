from repositories import MessageRepository
from typing import Optional
from datetime import datetime
from message_storage import Message


class MessageService:
    def __init__(self, repo: MessageRepository):
        self.repo = repo

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

        message = Message(
            chat_id=chat_id,
            user_id=user_id,
            role=role,
            content=cleaned_content,
            timestamp=datetime.now(),
            metadata=metadata,
        )
        return self.repo.save(message)

    def get_history(
        self,
        chat_id: int,
        user_id: "Optional[int]" = None,
        limit: int = 20,
        include_system: bool = True,
    ):
        # 대화 이력 비즈니스 로직 (예: 필터링, 가공 등)
        return self.repo.history(chat_id=chat_id, user_id=user_id, limit=limit, include_system=include_system)

    def get_all_messages(self, limit: int = 20):
        """
        전체 메시지를 최신순으로 limit만큼 반환
        """
        return self.repo.list_recent(limit=limit)

    def get_user_token_stats(self, user_id: int):
        """사용자별 토큰 사용량 통계 반환"""
        # 토큰 관련 서비스는 TokenService로 분리되었지만 기존 호환성용으로 호출을 위임할 수 있습니다.
        from repositories import TokenRepository
        token_repo = TokenRepository(self.repo.storage)
        return token_repo.user_stats(user_id)
