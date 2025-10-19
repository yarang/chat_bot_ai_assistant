import logging
from telegram import Update
from telegram.ext import ContextTypes
from services.chat_service import ChatService

logger = logging.getLogger(__name__)

class CommandHandlerService:
    def __init__(self, message_storage=None, chat_service: ChatService = None):
        self.message_storage = message_storage
        self.chat_service = chat_service

    async def set_persona(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not self.chat_service:
            return
        
        chat = update.effective_chat
        args = context.args
        if not args:
            await update.message.reply_text("사용법: /set_persona [페르소나 프롬프트]\n예: /set_persona 당신은 친절한 AI 비서입니다.")
            return

        persona_prompt = " ".join(args)
        logger.debug(f"[SET_PERSONA] Attempting to set persona for chat_id {chat.id}: '{persona_prompt}'")
        try:
            # upsert_chat을 사용하여 채팅 정보와 페르소나를 한 번에 저장
            self.chat_service.upsert_chat(
                chat_id=chat.id,
                chat_type=chat.type,
                title=chat.title,
                username=chat.username,
                persona_prompt=persona_prompt
            )

            # 저장 후 다시 불러와서 확인
            saved_persona = self.chat_service.get_persona(chat.id)
            logger.debug(f"[SET_PERSONA] Verification fetch for chat_id {chat.id}. Got: '{saved_persona}'")
            if saved_persona == persona_prompt:
                await update.message.reply_text(f"✅ 페르소나가 성공적으로 저장되었습니다:\n- {saved_persona}")
                logger.info(f"Persona set and verified for chat {chat.id}")
            else:
                await update.message.reply_text(f"⚠️ 페르소나 저장 확인에 실패했습니다. 저장된 값: '{saved_persona}'")
                logger.warning(f"Persona mismatch after setting for chat {chat.id}. Expected: '{persona_prompt}', Got: '{saved_persona}'")

        except Exception as e:
            logger.error(f"Error setting persona for chat {chat.id}: {str(e)}")
            await update.message.reply_text("❌ 페르소나 설정 중 오류가 발생했습니다.")

    async def get_persona(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not self.chat_service:
            return
        
        chat_id = update.effective_chat.id
        logger.debug(f"[GET_PERSONA] Getting persona for chat_id {chat_id}")
        try:
            persona_prompt = self.chat_service.get_persona(chat_id)
            logger.debug(f"[GET_PERSONA] Fetched persona for chat_id {chat_id}: '{persona_prompt}'")
            if persona_prompt:
                await update.message.reply_text(f"💬 현재 페르소나: {persona_prompt}")
            else:
                await update.message.reply_text("💬 설정된 페르소나가 없습니다.")
            logger.info(f"Persona retrieved for chat {chat_id}")
        except Exception as e:
            logger.error(f"Error getting persona for chat {chat.id}: {str(e)}")
            await update.message.reply_text("❌ 페르소나 조회 중 오류가 발생했습니다.")

    async def new(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Starts a new conversation by clearing the context, but not the stored messages."""
        if not update.message:
            logger.error("Update has no message attribute")
            return
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        try:
            if self.message_storage:
                # This method only clears the context for the next AI response,
                # it does not delete messages from the database.
                self.message_storage.clear_conversation_context(chat_id, user_id)
                await update.message.reply_text("✅ 새로운 대화를 시작합니다. 이제 새로운 페르소나(설정된 경우) 또는 컨텍스트로 대화할 수 있습니다.")
                logger.info(f"New conversation context started for chat {chat_id}, user {user_id}")
        except Exception as e:
            logger.error(f"Error starting new conversation for chat {chat_id}, user {user_id}: {str(e)}")
            await update.message.reply_text("❌ 새 대화를 시작하는 중 오류가 발생했습니다.")

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
• `/start` - 시작 메시지 보기
• `/help` - 이 도움말 보기
• `/new` - 새 대화 시작 (AI의 기억만 리셋)
• `/clear` - 모든 대화 기록 삭제
• `/set_persona [내용]` - AI의 역할 설정
• `/get_persona` - 현재 설정된 페르소나 확인
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
