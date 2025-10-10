from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class UserInfo:
    """사용자 정보 데이터 클래스"""
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    created_at: Optional[datetime] = None
