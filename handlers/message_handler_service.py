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
            current_message = message
            continuation_count = 0
            max_continuations = 3  # 무한 루프 방지를 위한 최대 연속 실행 횟수

            while continuation_count <= max_continuations:
                await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
                
                finish_reason = None
                response_buffer = ""
                full_response_text_from_gemini = ""
                telegram_message_limit = 4000  # A bit less than 4096 for safety

                # Use async for to stream and buffer the response chunks
                async for chunk in self.gemini_client.generate_response(
                    chat_id=update.effective_chat.id,
                    user_id=user.id,
                    message=current_message,
                    maintain_context=maintain_context
                ):
                    # Handle the finish_reason dictionary yielded at the end of the stream
                    if isinstance(chunk, dict) and 'finish_reason' in chunk:
                        finish_reason = chunk['finish_reason']
                        full_response_text_from_gemini = chunk.get('full_response_text', '')
                        continue

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
                
                # Check finish reason to decide whether to continue
                if finish_reason == 'MAX_TOKENS':
                    continuation_count += 1
                    if continuation_count <= max_continuations:
                        logger.warning(f"Response for user {user.id} was cut off due to MAX_TOKENS. Continuing... ({continuation_count}/{max_continuations})")
                        await update.message.reply_text("...답변이 길어 이어서 생성합니다...")
                        # 마지막 500자를 컨텍스트로 사용하여 더 자연스러운 연속 생성 유도
                        context_for_continuation = full_response_text_from_gemini[-500:]
                        current_message = (
                            f"이전 답변이 중간에 끊겼습니다. 다음 내용에 이어서 계속 작성해주세요.\n\n"
                            f"이전 내용 마지막 부분: \"...{context_for_continuation}\""
                        )
                        maintain_context = True # 컨텍스트는 계속 유지
                    else:
                        logger.warning(f"Max continuations reached for user {user.id}.")
                        await update.message.reply_text("⚠️ 답변이 너무 길어 여러 번에 걸쳐 전송했지만, 여전히 답변이 완료되지 않았을 수 있습니다.")
                        break # 루프 종료
                else:
                    # 응답이 잘리지 않았으면 루프 종료
                    break

            logger.info(f"Message handled for user {user.id}")
        except Exception as e:
            logger.error(f"Error handling message from user {user.id}: {str(e)}")
            error_message = "❌ 죄송합니다. 메시지 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
            await update.message.reply_text(error_message)
