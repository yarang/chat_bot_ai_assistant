"""
Telegram Bot Handlers and Logic with SQLite Storage
"""
import logging
from typing import Dict, Any
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
    def __init__(self, gemini_client, message_service, command_handler_service, message_handler_service, error_handler):
        self.gemini_client = gemini_client
        self.message_service = message_service
        self.command_handler_service = command_handler_service
        self.message_handler_service = message_handler_service
        self.error_handler_service = error_handler

    def setup_bot_handlers(self, app: Application, config: Dict[str, Any]) -> None:
        """
        Setup all bot command and message handlers with persistent storage
        """
        # 핸들러에 self를 전달하기 위해 partial 사용
        from functools import partial
        app.add_handler(CommandHandler("start", self.command_handler_service.start))
        app.add_handler(CommandHandler("help", self.command_handler_service.help))
        app.add_handler(CommandHandler("clear", self.command_handler_service.clear))
        # 추가 명령어 핸들러도 여기에 등록
        # clear, info, settings 등도 command_handler_service에 추가 구현 필요
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.message_handler_service.handle))
        app.add_error_handler(self.error_handler_service.handle)
        logger.info("Bot handlers setup complete with DI & SRP")

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