"""
Utility functions for application setup extracted from main.py.
"""
from telegram.ext import Application


def setup_telegram_app(config):
    """Setup Telegram application with handlers.

    Args:
        config (dict): Loaded configuration dictionary.

    Returns:
        telegram.ext.Application: Configured Telegram Application instance.
    """
    if not config:
        raise ValueError("Configuration not loaded")

    app = Application.builder().token(config["telegram"]["bot_token"]).build()

    # Local imports to avoid import-time side-effects
    from gemini_client import GeminiClient
    from message_storage import MessageStorage
    from services.message_service import MessageService
    from handlers.command_handler_service import CommandHandlerService
    from handlers.message_handler_service import MessageHandlerService
    from handlers.error_handler import ErrorHandler

    message_storage = MessageStorage()
    gemini_client = GeminiClient(config.get('gemini', {}), message_storage)
    message_service = MessageService(message_storage)
    command_handler_service = CommandHandlerService(message_storage=message_storage)
    message_handler_service = MessageHandlerService(gemini_client)
    error_handler_service = ErrorHandler()

    from bot import Bot

    bot = Bot(
        gemini_client,
        message_service,
        command_handler_service,
        message_handler_service,
        error_handler_service
    )
    bot.setup_bot_handlers(app, config)
    return app
