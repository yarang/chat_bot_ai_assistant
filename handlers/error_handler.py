import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

class ErrorHandler:
    async def handle(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.error(f"Exception while handling an update: {context.error}")
        if isinstance(update, Update) and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "❌ 시스템 오류가 발생했습니다. 관리자에게 문의해주세요."
                )
            except Exception:
                logger.error("Could not send error message to user")
