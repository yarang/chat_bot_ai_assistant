import logging
from typing import Optional

from repositories import ChatRepository
from models import ChatInfo

logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self, repo: ChatRepository):
        self.repo = repo

    def upsert_chat(
        self,
        chat_id: int,
        chat_type: str,
        title: Optional[str] = None,
        username: Optional[str] = None,
        persona_prompt: Optional[str] = None,  # 페르소나 프롬프트 추가
    ):
        """채팅 정보를 추가하거나 업데이트합니다. 페르소나 정보를 덮어쓰지 않도록 주의합니다."""
        logger.debug(f"[UPSERT_CHAT] Upserting chat_id {chat_id} with persona: '{persona_prompt}'")
        # 새 페르소나가 제공되지 않은 경우, 기존 페르소나를 유지합니다.
        if persona_prompt is None:
            existing_persona = self.get_persona(chat_id)
            logger.debug(f"[UPSERT_CHAT] No new persona provided. Existing persona for chat_id {chat_id}: '{existing_persona}'")
        else:
            existing_persona = persona_prompt

        chat = ChatInfo(
            chat_id=chat_id,
            chat_type=chat_type,
            title=title,
            username=username,
            persona_prompt=existing_persona,
        )
        self.repo.upsert(chat)

    def get_stats(self, chat_id: int):
        return self.repo.get_stats(chat_id)

    def set_persona(self, chat_id: int, persona_prompt: str):
        self.repo.update_persona(chat_id, persona_prompt)

    def get_persona(self, chat_id: int) -> Optional[str]:
        logger.debug(f"[GET_PERSONA_SVC] Getting persona for chat_id {chat_id}")
        persona = self.repo.get_persona(chat_id)
        logger.debug(f"[GET_PERSONA_SVC] Got persona for chat_id {chat_id}: '{persona}'")
        return persona
