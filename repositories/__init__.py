try:
	# Prefer package relative imports when used as a package
	from .user_repository import UserRepository  # type: ignore
	from .chat_repository import ChatRepository  # type: ignore
	from .message_repository import MessageRepository  # type: ignore
	from .token_repository import TokenRepository  # type: ignore
except Exception:
	# Fallback to absolute imports for some tooling/environments
	from repositories.user_repository import UserRepository  # type: ignore
	from repositories.chat_repository import ChatRepository  # type: ignore
	from repositories.message_repository import MessageRepository  # type: ignore
	from repositories.token_repository import TokenRepository  # type: ignore

__all__ = ["UserRepository", "ChatRepository", "MessageRepository", "TokenRepository"]
