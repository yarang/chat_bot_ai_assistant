from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict


@dataclass
class Message:
    """메시지 데이터 클래스"""
    chat_id: int
    user_id: int
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime
    message_id: Optional[int] = None
    metadata: Optional[Dict] = None
