from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ChatInfo:
    """채팅 정보 데이터 클래스"""
    chat_id: int
    chat_type: str  # 'private', 'group', 'supergroup', 'channel'
    title: Optional[str] = None
    username: Optional[str] = None
    created_at: Optional[datetime] = None
    persona_prompt: Optional[str] = None
