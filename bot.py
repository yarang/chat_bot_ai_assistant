"""
Telegram Bot Handlers and Logic with SQLite Storage
"""
import logging
from typing import Dict, Any, Optional
from telegram import Update
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    filters, 
    ContextTypes,
    CallbackQueryHandler
)
from telegram.error import TelegramError

from gemini_client import GeminiClient
from config_loader import get_gemini_config, get_app_config
from message_storage import MessageStorage
from models import UserInfo, ChatInfo

logger = logging.getLogger(__name__)


class Bot:
    """Bot container that holds references to services and sets up handlers.

    This class now supports dynamic registration/unregistration of services so
    new services can be added without changing the constructor signature.
    """
    def __init__(self, gemini_client=None, services: Optional[Dict[str, Any]] = None, **kwargs):
        # Core client kept as dedicated attribute for convenience
        self.gemini_client = gemini_client

        # Internal service registry
        self._services: Dict[str, Any] = {}

        # Accept a services dict or individual named services as kwargs for
        # backward compatibility with existing code.
        if services:
            if not isinstance(services, dict):
                raise TypeError("services must be a dict[str, Any]")
            self._services.update(services)

        # allow passing services as keyword args (e.g., message_service=...)
        self._services.update(kwargs)

        # Mirror common service names as attributes for convenience (optional)
        for name, svc in self._services.items():
            setattr(self, name, svc)

    def setup_bot_handlers(self, app: Application, config: Dict[str, Any]) -> None:
        """
        Setup all bot command and message handlers with persistent storage
        """
        # 핸들러에 self를 전달하기 위해 partial 사용
        from functools import partial

        # Resolve services from registry. This allows adding/removing
        # handler services without changing this class's signature.
        cmd_svc = self.get_service("command_handler_service")
        msg_svc = self.get_service("message_handler_service")
        err_svc = self.get_service("error_handler_service")

        if not cmd_svc:
            raise RuntimeError("command_handler_service is required to setup handlers")
        if not msg_svc:
            raise RuntimeError("message_handler_service is required to setup handlers")

        app.add_handler(CommandHandler("start", cmd_svc.start))
        app.add_handler(CommandHandler("help", cmd_svc.help))
        # only register clear if the service implements it
        if hasattr(cmd_svc, "clear"):
            app.add_handler(CommandHandler("clear", cmd_svc.clear))

        # Register text message handler
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg_svc.handle))

        # Register error handler if available
        if err_svc and hasattr(err_svc, "handle"):
            app.add_error_handler(err_svc.handle)

        logger.info("Bot handlers setup complete with DI & SRP")

    # --- Dynamic service registry API -------------------------------------------------
    def register_service(self, name: str, service: Any) -> None:
        """Register a service under a string name.

        Also exposes the service as an attribute on the Bot instance for
        convenience (e.g., bot.command_handler_service).
        """
        if not name or not isinstance(name, str):
            raise ValueError("service name must be a non-empty string")
        self._services[name] = service
        setattr(self, name, service)

    def get_service(self, name: str, default: Any = None) -> Any:
        """Retrieve a registered service by name."""
        return self._services.get(name, default)

    def unregister_service(self, name: str) -> None:
        """Remove a service from the registry and delete attribute mirror."""
        if name in self._services:
            del self._services[name]
        if hasattr(self, name):
            try:
                delattr(self, name)
            except Exception:
                # best-effort removal of attribute
                pass

    def list_services(self) -> Dict[str, Any]:
        """Return a shallow copy of registered services."""
        return dict(self._services)

    # 핸들러 책임은 각 서비스로 위임


# Additional utility functions
def is_admin(user_id: int) -> bool:
    """Check if user is admin (implement your admin logic here)"""
    # You can add admin user IDs here or implement database check
    admin_ids = []  # Add admin user IDs here
    return user_id in admin_ids

async def broadcast_message(context: ContextTypes.DEFAULT_TYPE, message: str, user_ids: list) -> None:
    """Broadcast message to multiple users (admin function)"""
    success_count = 0
    for user_id in user_ids:
        try:
            await context.bot.send_message(chat_id=user_id, text=message)
            success_count += 1
        except TelegramError as e:
            logger.error(f"Failed to send broadcast to user {user_id}: {str(e)}")
    
    logger.info(f"Broadcast sent to {success_count}/{len(user_ids)} users")