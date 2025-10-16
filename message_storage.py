"""
SQLite 기반 메시지 히스토리 저장소
채팅방별, 사용자별 메시지 관리 시스템
"""
import sqlite3
import re
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import threading
from contextlib import contextmanager
from internal.db_instance import engine as _engine, SessionLocal as _SessionLocal, get_connection as _get_connection

from models import Message, ChatInfo, UserInfo

logger = logging.getLogger(__name__)

class MessageStorage:
    def clear_conversation(self, chat_id: int, user_id: int) -> int:
        """
        해당 채팅방(chat_id)과 사용자(user_id)의 모든 메시지를 삭제
        Returns: 삭제된 메시지 개수
        """
        from sqlalchemy import text
        with self._lock:
            with self._get_connection() as conn:
                with conn.begin():
                    cursor = conn.execute(text("DELETE FROM messages WHERE chat_id = :chat_id AND user_id = :user_id"), {"chat_id": chat_id, "user_id": user_id})
                return cursor.rowcount
    """SQLite 기반 메시지 저장소"""
    
    def __init__(self, db_path: str = "bot_messages.db"):
        """
        초기화
        
        Args:
            db_path: SQLite 데이터베이스 파일 경로
        """
        self.db_path = db_path
        # use db_instance engine/session created by internal/db_instance.py
        self._lock = threading.Lock()
        # keep db_path for compatibility but prefer engine from db_instance.py
        self._SessionLocal = _SessionLocal
        self._engine = _engine
        # initialize schema using the provided engine/connection
        self._init_database()
        
    def _add_column_if_not_exists(self, conn, table_name: str, column_name: str, column_def: str):
        """
        테이블에 특정 컬럼이 존재하지 않으면 추가합니다.
        """
        try:
            # sanitize table name to avoid SQL injection for PRAGMA/DDL
            if not re.match(r'^[A-Za-z0-9_]+$', table_name):
                raise ValueError("invalid table name")

            # Use driver-level exec to run PRAGMA and DDL statements which are
            # not always accepted as SQLAlchemy 'text' executables in all
            # configurations.
            result = conn.exec_driver_sql(f"PRAGMA table_info({table_name})")
            # Use mappings() to get dict-like rows so we can access by column name
            mappings = result.mappings().fetchall()
            columns = [row['name'] for row in mappings]
            if column_name not in columns:
                logger.info(f"Adding column '{column_name}' to table '{table_name}'...")
                conn.exec_driver_sql(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}")
                logger.info(f"Column '{column_name}' added to table '{table_name}'.")
        except sqlite3.Error as e:
            # 테이블이 아직 존재하지 않는 경우 등 PRAGMA에서 오류가 발생할 수 있음
            logger.warning(f"Could not check/add column '{column_name}' to '{table_name}': {e}")

    def _init_database(self):
        """데이터베이스 및 테이블 초기화"""
        from sqlalchemy import text
        with self._get_connection() as conn:
            # run schema creation inside a single transaction
            with conn.begin():
                # 사용자 정보 테이블
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        last_name TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))

                # 채팅 정보 테이블
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS chats (
                        chat_id INTEGER PRIMARY KEY,
                        chat_type TEXT NOT NULL,
                        title TEXT,
                        username TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))

                # 메시지 테이블
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        chat_id INTEGER NOT NULL,
                        user_id INTEGER NOT NULL,
                        role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                        content TEXT NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        interaction_id TEXT,
                        metadata TEXT,
                        FOREIGN KEY (user_id) REFERENCES users (user_id),
                        FOREIGN KEY (chat_id) REFERENCES chats (chat_id)
                    )
                """))

                # 토큰 사용량 테이블
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS token_usage (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        chat_id INTEGER NOT NULL,
                        message_id INTEGER,
                        interaction_id TEXT,
                        role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                        tokens INTEGER NOT NULL DEFAULT 0,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id),
                        FOREIGN KEY (chat_id) REFERENCES chats (chat_id),
                        FOREIGN KEY (message_id) REFERENCES messages (id)
                    )
                """))

                # 인덱스 생성 (성능 향상)
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_messages_chat_timestamp ON messages (chat_id, timestamp DESC)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_messages_user_timestamp ON messages (user_id, timestamp DESC)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_messages_interaction_id ON messages (interaction_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_messages_chat_user ON messages (chat_id, user_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_token_usage_user_ts ON token_usage (user_id, timestamp DESC)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_token_usage_chat_user ON token_usage (chat_id, user_id)"))

            # 스키마 마이그레이션: interaction_id 컬럼 추가
            self._add_column_if_not_exists(conn, 'messages', 'interaction_id', 'TEXT')
            self._add_column_if_not_exists(conn, 'token_usage', 'interaction_id', 'TEXT')

        logger.info(f"Database initialized: {self.db_path}")
    
    @contextmanager
    def _get_connection(self):
        """Compatibility wrapper around the centralized DBSession.get_connection.

        Keeps the same API (contextmanager) used across the codebase.
        """
        # _get_connection from db_instance expects the engine as first arg
        with _get_connection(self._engine) as conn:
            yield conn
    
    def save_user(self, user_info: UserInfo) -> None:
        """사용자 정보 저장/업데이트"""
        with self._lock:
            with self._get_connection() as conn:
                from sqlalchemy import text
                with conn.begin():
                    conn.execute(text("""
                        INSERT OR REPLACE INTO users (user_id, username, first_name, last_name)
                        VALUES (:user_id, :username, :first_name, :last_name)
                    """), {"user_id": user_info.user_id, "username": user_info.username, "first_name": user_info.first_name, "last_name": user_info.last_name})
    
    def save_chat(self, chat_info: ChatInfo) -> None:
        """채팅 정보 저장/업데이트"""
        with self._lock:
            with self._get_connection() as conn:
                from sqlalchemy import text
                with conn.begin():
                    conn.execute(text("""
                        INSERT OR REPLACE INTO chats (chat_id, chat_type, title, username)
                        VALUES (:chat_id, :chat_type, :title, :username)
                    """), {"chat_id": chat_info.chat_id, "chat_type": chat_info.chat_type, "title": chat_info.title, "username": chat_info.username})
    
    def save_message(self, message: Message) -> int:
        """
        메시지 저장
        
        Args:
            message: 저장할 메시지
            
        Returns:
            메시지 ID
        """
        with self._lock:
            with self._get_connection() as conn:
                from sqlalchemy import text
                metadata_json = json.dumps(message.metadata) if message.metadata else None
                # interaction_id를 Message 객체에서 가져오거나 None으로 설정
                interaction_id = getattr(message, 'interaction_id', None)
                with conn.begin():
                    cursor = conn.execute(text("""
                        INSERT INTO messages (chat_id, user_id, role, content, timestamp, metadata, interaction_id)
                        VALUES (:chat_id, :user_id, :role, :content, :timestamp, :metadata, :interaction_id)
                    """), {
                        "chat_id": message.chat_id,
                        "user_id": message.user_id,
                        "role": message.role,
                        "content": message.content,
                        "timestamp": message.timestamp or datetime.now(),
                        "metadata": metadata_json,
                        "interaction_id": interaction_id,
                    })
                    try:
                        lastrowid = cursor.lastrowid or 0
                    except Exception:
                        lastrowid = (cursor.inserted_primary_key[0] if hasattr(cursor, 'inserted_primary_key') and cursor.inserted_primary_key else 0)
                return int(lastrowid)
    
    def get_conversation_history(
        self, 
        chat_id: int, 
        user_id: Optional[int] = None,
        limit: int = 20,
        include_system: bool = True
    ) -> List[Message]:
        """
        대화 기록 조회
        
        Args:
            chat_id: 채팅 ID
            user_id: 특정 사용자만 조회 (None이면 모든 사용자)
            limit: 최대 메시지 수
            include_system: 시스템 메시지(assistant) 포함 여부
            
        Returns:
            메시지 목록 (시간순 정렬)
        """
        from sqlalchemy import text
        with self._get_connection() as conn:
            sql = "SELECT * FROM messages WHERE chat_id = :chat_id"
            params = {"chat_id": chat_id, "limit": limit}

            if user_id is not None:
                sql += " AND user_id = :user_id"
                params["user_id"] = user_id

            if not include_system:
                sql += " AND role = 'user'"

            sql += " ORDER BY timestamp DESC LIMIT :limit"

            result = conn.execute(text(sql), params)
            rows = result.mappings().fetchall()
            
            messages = []
            for row in reversed(rows):  # 시간순으로 정렬
                metadata = json.loads(row['metadata']) if row['metadata'] else None
                message = Message(
                    message_id=row['id'],
                    chat_id=row['chat_id'],
                    user_id=row['user_id'],
                    role=row['role'],
                    content=row['content'],
                    timestamp=datetime.fromisoformat(row['timestamp']),
                    metadata=metadata
                )
                messages.append(message)
            
            return messages
    
    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """사용자 통계 조회"""
        from sqlalchemy import text
        with self._get_connection() as conn:
            # 총 메시지 수
            result = conn.execute(text("""
                SELECT COUNT(*) as total_messages,
                       COUNT(CASE WHEN role = 'user' THEN 1 END) as user_messages,
                       COUNT(CASE WHEN role = 'assistant' THEN 1 END) as assistant_messages,
                       MIN(timestamp) as first_message,
                       MAX(timestamp) as last_message
                FROM messages 
                WHERE user_id = :user_id
            """), {"user_id": user_id})
            row = result.mappings().fetchone() or {}
            stats = dict(row)

            # 채팅방별 메시지 수
            result = conn.execute(text("""
                SELECT chat_id, COUNT(*) as message_count
                FROM messages 
                WHERE user_id = :user_id
                GROUP BY chat_id
                ORDER BY message_count DESC
            """), {"user_id": user_id})
            stats['chats'] = [dict(r) for r in result.mappings().fetchall()]

            # 토큰 사용량 통계 추가
            result = conn.execute(text("""
                SELECT SUM(tokens) as total_tokens,
                       SUM(CASE WHEN role = 'user' THEN tokens ELSE 0 END) as user_tokens,
                       SUM(CASE WHEN role = 'assistant' THEN tokens ELSE 0 END) as assistant_tokens
                FROM token_usage
                WHERE user_id = :user_id
            """), {"user_id": user_id})
            token_row = result.mappings().fetchone() or {}
            stats['token_usage'] = {
                'total_tokens': token_row.get('total_tokens', 0) or 0,
                'user_tokens': token_row.get('user_tokens', 0) or 0,
                'assistant_tokens': token_row.get('assistant_tokens', 0) or 0,
            }

            return stats
    
    def get_user_chat_list(self, user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """특정 사용자가 참여한 채팅방 목록 및 요약 정보 반환"""
        from sqlalchemy import text
        with self._get_connection() as conn:
            result = conn.execute(text("""
                SELECT 
                    c.chat_id,
                    c.chat_type,
                    c.title,
                    c.username,
                    COUNT(m.id) AS message_count,
                    MAX(m.timestamp) AS last_message_at
                FROM messages m
                LEFT JOIN chats c ON m.chat_id = c.chat_id
                WHERE m.user_id = :user_id
                GROUP BY c.chat_id, c.chat_type, c.title, c.username
                ORDER BY last_message_at DESC
                LIMIT :limit
            """), {"user_id": user_id, "limit": limit})

            chat_rows = result.mappings().fetchall()
            chat_list: List[Dict[str, Any]] = []
            for row in chat_rows:
                last_message_ts = row.get("last_message_at")
                if isinstance(last_message_ts, str):
                    last_message_at = last_message_ts
                elif last_message_ts is None:
                    last_message_at = None
                else:
                    last_message_at = last_message_ts.isoformat()

                chat_list.append({
                    "chat_id": row.get("chat_id"),
                    "chat_type": row.get("chat_type"),
                    "title": row.get("title"),
                    "username": row.get("username"),
                    "message_count": int(row.get("message_count", 0) or 0),
                    "last_message_at": last_message_at
                })
            return chat_list

    def save_token_usage(self, user_id: int, chat_id: int, tokens: int, role: str = 'user', message_id: Optional[int] = None, timestamp: Optional[datetime] = None, interaction_id: Optional[str] = None) -> int:
        """
        토큰 사용량 기록 저장

        Returns: token_usage id
        """
        with self._lock:
            from sqlalchemy import text
            with self._get_connection() as conn:
                ts = timestamp or datetime.now()
                with conn.begin():
                    cursor = conn.execute(text("""
                        INSERT INTO token_usage (user_id, chat_id, message_id, interaction_id, role, tokens, timestamp)
                        VALUES (:user_id, :chat_id, :message_id, :interaction_id, :role, :tokens, :ts)
                    """), {"user_id": user_id, "chat_id": chat_id, "message_id": message_id, "interaction_id": interaction_id, "role": role, "tokens": tokens, "ts": ts})
                    try:
                        lastrowid = cursor.lastrowid or 0
                    except Exception:
                        lastrowid = (cursor.inserted_primary_key[0] if hasattr(cursor, 'inserted_primary_key') and cursor.inserted_primary_key else 0)
                return int(lastrowid)

    def get_user_token_stats(self, user_id: int) -> Dict[str, Any]:
        """사용자별 토큰 통계 반환"""
        from sqlalchemy import text
        with self._get_connection() as conn:
            result = conn.execute(text("""
                SELECT SUM(tokens) as total_tokens,
                       COUNT(*) as records,
                       MIN(timestamp) as first_record,
                       MAX(timestamp) as last_record
                FROM token_usage
                WHERE user_id = :user_id
            """), {"user_id": user_id})
            row = result.mappings().fetchone() or {}
            stats = {
                'total_tokens': row.get('total_tokens', 0) or 0,
                'records': row.get('records', 0) or 0,
                'first_record': row.get('first_record'),
                'last_record': row.get('last_record')
            }

            # 채팅방별 토큰 합계
            result = conn.execute(text("""
                SELECT chat_id, SUM(tokens) as tokens
                FROM token_usage
                WHERE user_id = :user_id
                GROUP BY chat_id
                ORDER BY tokens DESC
            """), {"user_id": user_id})
            stats['by_chat'] = [dict(r) for r in result.mappings().fetchall()]

            return stats
    
    def get_chat_stats(self, chat_id: int) -> Dict[str, Any]:
        """채팅방 통계 조회"""
        from sqlalchemy import text
        with self._get_connection() as conn:
            # 기본 통계
            result = conn.execute(text("""
                SELECT COUNT(*) as total_messages,
                       COUNT(DISTINCT user_id) as unique_users,
                       MIN(timestamp) as first_message,
                       MAX(timestamp) as last_message
                FROM messages 
                WHERE chat_id = :chat_id
            """), {"chat_id": chat_id})
            
            stats = dict(result.mappings().fetchone() or {})
            
            # 사용자별 메시지 수
            result = conn.execute(text("""
                SELECT u.username, u.first_name, m.user_id, COUNT(*) as message_count
                FROM messages m
                LEFT JOIN users u ON m.user_id = u.user_id
                WHERE m.chat_id = :chat_id
                GROUP BY m.user_id
                ORDER BY message_count DESC
            """), {"chat_id": chat_id})
            
            stats['users'] = [dict(row) for row in result.mappings().fetchall()]
            
            return stats
    
    def search_messages(
        self, 
        query: str, 
        chat_id: Optional[int] = None,
        user_id: Optional[int] = None,
        limit: int = 50
    ) -> List[Message]:
        """
        메시지 검색
        
        Args:
            query: 검색어
            chat_id: 특정 채팅방에서만 검색
            user_id: 특정 사용자 메시지만 검색
            limit: 최대 결과 수
            
        Returns:
            검색 결과 메시지 목록
        """
        from sqlalchemy import text
        with self._get_connection() as conn:
            sql = "SELECT m.*, t.tokens FROM messages m LEFT JOIN token_usage t ON m.id = t.message_id WHERE m.content LIKE :q"
            params = {"q": f"%{query}%", "limit": limit}

            if chat_id is not None:
                sql += " AND chat_id = :chat_id"
                params["chat_id"] = chat_id

            if user_id is not None:
                sql += " AND user_id = :user_id"
                params["user_id"] = user_id

            sql += " ORDER BY timestamp DESC LIMIT :limit"

            result = conn.execute(text(sql), params)
            rows = result.mappings().fetchall()
            
            messages = []
            for row in rows:
                metadata = json.loads(row['metadata']) if row['metadata'] else None
                message = Message(
                    message_id=row['id'],
                    chat_id=row['chat_id'],
                    user_id=row['user_id'],
                    role=row['role'],
                    content=row['content'],
                    timestamp=datetime.fromisoformat(row['timestamp']),
                    metadata=metadata
                )
                setattr(message, 'tokens', row['tokens'] if row['tokens'] is not None else 0)
                messages.append(message)
            
            return messages
    
    def cleanup_old_messages(self, days_to_keep: int = 30) -> int:
        """
        오래된 메시지 정리
        
        Args:
            days_to_keep: 보관할 일수
            
        Returns:
            삭제된 메시지 수
        """
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        from sqlalchemy import text
        with self._lock:
            with self._get_connection() as conn:
                with conn.begin():
                    cursor = conn.execute(text("DELETE FROM messages WHERE timestamp < :cutoff"), {"cutoff": cutoff_date})
                deleted_count = cursor.rowcount

                # VACUUM으로 디스크 공간 회수
                # Use driver-level execution for VACUUM which is DDL-like
                conn.exec_driver_sql("VACUUM")

                logger.info(f"Cleaned up {deleted_count} old messages")
                return deleted_count
    
    def get_database_stats(self) -> Dict[str, Any]:
        """데이터베이스 전체 통계"""
        from sqlalchemy import text
        with self._get_connection() as conn:
            stats = {}

            # 테이블별 레코드 수
            for table in ['users', 'chats', 'messages']:
                cursor = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                stats[f'{table}_count'] = cursor.fetchone()[0]

            # 데이터베이스 크기
            cursor = conn.exec_driver_sql("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
            stats['db_size_bytes'] = cursor.fetchone()[0]
            stats['db_size_mb'] = round(stats['db_size_bytes'] / 1024 / 1024, 2)

            # 최근 활동
            cursor = conn.execute(text("""
                SELECT DATE(timestamp) as date, COUNT(*) as message_count
                FROM messages 
                WHERE timestamp >= date('now', '-7 days')
                GROUP BY DATE(timestamp)
                ORDER BY date DESC
            """))
            stats['recent_activity'] = cursor.mappings().fetchall()
            # 전체 토큰 사용량 요약
            try:
                cursor = conn.execute(text("SELECT SUM(tokens) as total_tokens FROM token_usage"))
                stats['total_tokens'] = cursor.fetchone()[0] or 0
            except Exception:
                stats['total_tokens'] = 0

            # 채널별 유니크 유저 수
            try:
                cursor = conn.execute(text("SELECT COUNT(*) FROM (SELECT DISTINCT chat_id, user_id FROM messages)"))
                stats['unique_user_chat_count'] = cursor.fetchone()[0]
            except Exception:
                stats['unique_user_chat_count'] = 0

            return stats

    def reset_database(self) -> None:
        """
        데이터베이스의 모든 테이블을 삭제하고 재생성합니다.
        주의: 모든 데이터가 삭제됩니다.
        """
        from sqlalchemy import text
        with self._lock:
            with self._get_connection() as conn:
                logger.warning("Resetting database. All data will be lost.")
                tables = ['users', 'chats', 'messages', 'token_usage']
                with conn.begin():
                    for table in tables:
                        conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
        self._init_database()
        logger.info("Database has been reset.")
    
    def export_chat_history(self, chat_id: int, format: str = 'json') -> str:
        """
        채팅 기록 내보내기
        
        Args:
            chat_id: 채팅 ID
            format: 내보내기 형식 ('json' 또는 'txt')
            
        Returns:
            내보낸 데이터 문자열
        """
        messages = self.get_conversation_history(chat_id, limit=10000)
        
        if format == 'json':
            data = []
            for msg in messages:
                data.append({
                    'timestamp': msg.timestamp.isoformat(),
                    'user_id': msg.user_id,
                    'role': msg.role,
                    'content': msg.content,
                    'metadata': msg.metadata
                })
            return json.dumps(data, indent=2, ensure_ascii=False)
        
        elif format == 'txt':
            lines = []
            for msg in messages:
                timestamp = msg.timestamp.strftime('%Y-%m-%d %H:%M:%S')
                role = "👤 사용자" if msg.role == 'user' else "🤖 봇"
                lines.append(f"[{timestamp}] {role}: {msg.content}")
            return '\n'.join(lines)
        
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def close(self):
        """리소스 정리"""
        # SQLite는 자동으로 연결이 닫히므로 특별한 정리가 필요 없음
        logger.info("MessageStorage closed")
