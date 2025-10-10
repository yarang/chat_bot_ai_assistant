import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

class MessageHandlerService:
    def __init__(self, gemini_client):
        self.gemini_client = gemini_client

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        message = getattr(update.message, 'text', None)
        if not message:
            logger.error("Update message has no text")
            return
        max_length = 4000
        if len(message) > max_length:
            await update.message.reply_text(
                f"❌ 메시지가 너무 깁니다. 최대 {max_length}자까지 입력 가능합니다."
            )
            return
        try:
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
            response = await self.gemini_client.generate_response(
                chat_id=update.effective_chat.id,
                user_id=user.id,
                message=message
            )
            max_telegram_length = 4096
            if len(response) > max_telegram_length:
                chunks = [response[i:i+max_telegram_length] for i in range(0, len(response), max_telegram_length)]
                for chunk in chunks:
                    await update.message.reply_text(chunk)
            else:
                await update.message.reply_text(response)
            logger.info(f"Message handled for user {user.id}")
        except Exception as e:
            logger.error(f"Error handling message from user {user.id}: {str(e)}")
            error_message = "❌ 죄송합니다. 메시지 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
            await update.message.reply_text(error_message)
