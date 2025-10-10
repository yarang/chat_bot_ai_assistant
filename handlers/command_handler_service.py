import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

class CommandHandlerService:
    def __init__(self, message_storage=None):
        self.message_storage = message_storage

    async def clear(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message:
            logger.error("Update has no message attribute")
            return
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        try:
            if self.message_storage:
                deleted_count = self.message_storage.clear_conversation(chat_id, user_id)
                await update.message.reply_text(f"✅ 대화 기록이 초기화되었습니다. 삭제된 메시지: {deleted_count}개")
                logger.info(f"Conversation cleared for chat {chat_id}, user {user_id}")
            else:
                await update.message.reply_text("❌ 내부 오류: message_storage가 연결되어 있지 않습니다.")
        except Exception as e:
            logger.error(f"Error clearing conversation for chat {chat_id}, user {user_id}: {str(e)}")
            await update.message.reply_text("❌ 대화 기록 초기화 중 오류가 발생했습니다.")
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        welcome_message = f"""
🤖 안녕하세요 {getattr(user, 'first_name', '사용자')}님!
저는 Google Gemini AI를 사용하는 챗봇입니다.
📋 사용 가능한 명령어:
• /help - 도움말 보기
• /clear - 대화 기록 초기화
• /info - 봇 정보 보기
• /settings - 설정 보기
💬 저에게 아무 메시지나 보내주시면 AI가 답변해드립니다!
        """
        try:
            if not update.message:
                logger.error("Update has no message attribute")
                return 
            await update.message.reply_text(welcome_message)
            logger.info(f"Start command sent to user {getattr(user, 'id', 'unknown')}")
        except Exception as e:
            logger.error(f"Error sending start message: {str(e)}")

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        help_message = """
🔧 **도움말**
• 저에게 아무 메시지나 보내주세요
• AI가 자동으로 답변해드립니다
• 대화 기록이 영구 보관됩니다
• `/start` - 시작 메시지 보기
• `/help` - 이 도움말 보기
• `/clear` - 대화 기록 정보 보기
• `/info` - 봇 및 AI 모델 정보
• `/settings` - 현재 설정 보기
• `/stats` - 개인 및 채팅 통계
• `/search 검색어` - 메시지 검색
• `/export` - 대화 기록 내보내기
❓ 문제가 있으시면 언제든 문의해주세요!
        """
        try:
            if not update.message:
                logger.error("Update has no message attribute")
                return
            await update.message.reply_text(help_message)
            logger.info(f"Help command sent to user {getattr(update.effective_user, 'id', 'unknown')}")
        except Exception as e:
            logger.error(f"Error sending help message: {str(e)}")
