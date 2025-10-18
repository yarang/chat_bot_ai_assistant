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

        # Check if a new conversation should be started
        start_new_conversation = context.user_data.get('new_conversation', False)
        if start_new_conversation:
            maintain_context = False
            context.user_data['new_conversation'] = False  # Reset the flag
            logger.info(f"Handling message for user {user.id} with new conversation context.")
        else:
            maintain_context = True

        try:
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
            
            # Buffer for combining response chunks
            response_buffer = ""
            telegram_message_limit = 4000  # A bit less than 4096 for safety

            # Use async for to stream and buffer the response chunks
            async for chunk in self.gemini_client.generate_response(
                chat_id=update.effective_chat.id,
                user_id=user.id,
                message=message,
                maintain_context=maintain_context  # Pass the context flag
            ):
                if chunk:
                    response_buffer += chunk
                    # When buffer exceeds the limit, find a good split point and send
                    while len(response_buffer) > telegram_message_limit:
                        # Find the last newline to split gracefully
                        split_pos = response_buffer.rfind('\n', 0, telegram_message_limit)
                        
                        # If no newline found, force split at the limit (less ideal but necessary)
                        if split_pos == -1:
                            split_pos = telegram_message_limit
                        
                        message_to_send = response_buffer[:split_pos]
                        response_buffer = response_buffer[split_pos:].lstrip()

                        if message_to_send.strip():
                            await update.message.reply_text(message_to_send)

            # Send any remaining text in the buffer after the loop finishes
            if response_buffer.strip():
                await update.message.reply_text(response_buffer)

            logger.info(f"Message handled for user {user.id}")
        except Exception as e:
            logger.error(f"Error handling message from user {user.id}: {str(e)}")
            error_message = "❌ 죄송합니다. 메시지 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
            await update.message.reply_text(error_message)
