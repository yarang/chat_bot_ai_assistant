"""
Telegram Bot Handlers and Logic
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

logger = logging.getLogger(__name__)

# Global Gemini client
gemini_client = None

def setup_bot_handlers(app: Application, config: Dict[str, Any]) -> None:
    """
    Setup all bot command and message handlers
    
    Args:
        app: Telegram Application instance
        config: Configuration dictionary
    """
    global gemini_client
    
    # Initialize Gemini client
    gemini_config = get_gemini_config(config)
    gemini_client = GeminiClient(gemini_config)
    
    # Add handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(CommandHandler("info", info_command))
    app.add_handler(CommandHandler("settings", settings_command))
    
    # Message handler for AI chat
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Error handler
    app.add_error_handler(error_handler)
    
    logger.info("Bot handlers setup complete")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command"""
    user = update.effective_user
    welcome_message = f"""
🤖 안녕하세요 {user.first_name}님!

저는 Google Gemini AI를 사용하는 챗봇입니다.

📋 사용 가능한 명령어:
• /help - 도움말 보기
• /clear - 대화 기록 초기화
• /info - 봇 정보 보기
• /settings - 설정 보기

💬 저에게 아무 메시지나 보내주시면 AI가 답변해드립니다!
    """
    
    try:
        await update.message.reply_text(welcome_message)
        logger.info(f"Start command sent to user {user.id}")
    except TelegramError as e:
        logger.error(f"Error sending start message: {str(e)}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command"""
    help_message = """
🔧 **도움말**

**기본 사용법:**
• 저에게 아무 메시지나 보내주세요
• AI가 자동으로 답변해드립니다
• 대화 맥락이 유지됩니다

**명령어:**
• `/start` - 시작 메시지 보기
• `/help` - 이 도움말 보기
• `/clear` - 대화 기록 초기화
• `/info` - 봇 및 AI 모델 정보
• `/settings` - 현재 설정 보기

**팁:**
• 긴 대화를 나눌 때는 가끔 `/clear`로 초기화하세요
• 구체적인 질문일수록 더 정확한 답변을 받을 수 있습니다
• 한국어와 영어 모두 지원합니다

❓ 문제가 있으시면 언제든 문의해주세요!
    """
    
    try:
        await update.message.reply_markdown_v2(help_message)
        logger.info(f"Help command sent to user {update.effective_user.id}")
    except TelegramError as e:
        logger.error(f"Error sending help message: {str(e)}")

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /clear command"""
    user_id = update.effective_user.id
    
    try:
        conversation_length = gemini_client.get_conversation_length(user_id)
        gemini_client.clear_conversation(user_id)
        
        message = f"✅ 대화 기록이 초기화되었습니다.\n(이전 대화: {conversation_length}개 메시지)"
        await update.message.reply_text(message)
        
        logger.info(f"Conversation cleared for user {user_id}")
    except Exception as e:
        logger.error(f"Error clearing conversation for user {user_id}: {str(e)}")
        await update.message.reply_text("❌ 대화 기록 초기화 중 오류가 발생했습니다.")

async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /info command"""
    try:
        model_info = gemini_client.get_model_info()
        user_id = update.effective_user.id
        conversation_length = gemini_client.get_conversation_length(user_id)
        
        info_message = f"""
🤖 **봇 정보**

**AI 모델:** {model_info['model_name']}
**활성 대화:** {model_info['active_conversations']}개
**현재 대화 길이:** {conversation_length}개 메시지

**모델 설정:**
• 온도: {model_info['temperature']}
• 최대 토큰: {model_info['max_tokens']}
• Top-p: {model_info['top_p']}
• Top-k: {model_info['top_k']}

🔄 **버전:** 1.0.0
⚡ **상태:** 정상 작동 중
        """
        
        await update.message.reply_markdown_v2(info_message)
        logger.info(f"Info command sent to user {user_id}")
    except Exception as e:
        logger.error(f"Error sending info message: {str(e)}")
        await update.message.reply_text("❌ 정보를 가져오는 중 오류가 발생했습니다.")

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /settings command"""
    try:
        model_info = gemini_client.get_model_info()
        
        settings_message = f"""
⚙️ **현재 설정**

**AI 모델 설정:**
• 모델: `{model_info['model_name']}`
• 창의성 (Temperature): `{model_info['temperature']}`
• 응답 길이 (Max Tokens): `{model_info['max_tokens']}`
• 다양성 (Top-p): `{model_info['top_p']}`
• 선택성 (Top-k): `{model_info['top_k']}`

💡 **설정 설명:**
• **창의성**: 높을수록 더 창의적이고 예측 불가능한 답변
• **응답 길이**: 생성할 수 있는 최대 텍스트 길이
• **다양성**: 단어 선택의 다양성 조절
• **선택성**: 고려할 단어 후보의 수

현재 설정을 변경하려면 관리자에게 문의하세요.
        """
        
        await update.message.reply_markdown_v2(settings_message)
        logger.info(f"Settings command sent to user {update.effective_user.id}")
    except Exception as e:
        logger.error(f"Error sending settings message: {str(e)}")
        await update.message.reply_text("❌ 설정 정보를 가져오는 중 오류가 발생했습니다.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle regular text messages"""
    user = update.effective_user
    message = update.message.text
    
    # Check message length
    max_length = 4000  # Default max length
    if len(message) > max_length:
        await update.message.reply_text(
            f"❌ 메시지가 너무 깁니다. 최대 {max_length}자까지 입력 가능합니다."
        )
        return
    
    try:
        # Show typing indicator
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        # Generate response using Gemini
        response = await gemini_client.generate_response(user.id, message)
        
        # Split response if too long for Telegram
        max_telegram_length = 4096
        if len(response) > max_telegram_length:
            # Split into chunks
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

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors in bot"""
    logger.error(f"Exception while handling an update: {context.error}")
    
    # Notify user if possible
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "❌ 시스템 오류가 발생했습니다. 관리자에게 문의해주세요."
            )
        except TelegramError:
            # If we can't send message, just log it
            logger.error("Could not send error message to user")

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