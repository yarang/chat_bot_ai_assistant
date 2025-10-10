"""
Telegram Bot with Gemini AI - Main FastAPI Application
"""
import json
import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from telegram.ext import Application
import uvicorn

from config_loader import load_config
from logging_setup import setup_logging
from internal.utils import setup_telegram_app

logger = logging.getLogger(__name__)

# Global variables
telegram_app = None
config = None
message_history = []  # Store recent messages for monitoring

# Setup templates
templates = Jinja2Templates(directory="templates")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan"""
    global telegram_app, config
    
    # Startup
    config = load_config()
    setup_logging(config)  # Setup logging
    telegram_app = setup_telegram_app(config)
    
    # Initialize bot
    await telegram_app.initialize()
    await telegram_app.start()
    
    # Set webhook
    webhook_url = f"{config['telegram']['webhook_url']}{config['telegram']['webhook_path']}"
    await telegram_app.bot.set_webhook(webhook_url)
    
    logger.info(f"Bot started with webhook: {webhook_url}")
    
    yield
    
    # Shutdown
    await telegram_app.stop()
    await telegram_app.shutdown()
    logger.info("Bot stopped")

# setup_telegram_app is provided by internal.utils.setup_telegram_app

# Create FastAPI app
app = FastAPI(
    title="Telegram Gemini Bot",
    description="A Telegram bot powered by Google Gemini AI",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "message": "Telegram Gemini Bot is running"}

@app.post("/webhook")
async def webhook(request: Request):
    """Handle incoming Telegram webhooks"""
    try:
        # Get the update from Telegram
        update_data = await request.json()
        from telegram import Update
        update = Update.de_json(update_data, telegram_app.bot)
        
        # Store message for monitoring (keep last 100 messages)
        if update.message:
            from message_storage import MessageStorage, UserInfo, ChatInfo
            storage = MessageStorage()

            message_info = {
                "timestamp": update.message.date.isoformat(),
                "user_id": update.message.from_user.id,
                "username": update.message.from_user.username or "Unknown",
                "first_name": update.message.from_user.first_name or "Unknown",
                "message": update.message.text or "[Non-text message]",
                "chat_id": update.message.chat_id
            }
            message_history.append(message_info)
            if len(message_history) > 100:
                message_history.pop(0)

            # --- 사용자 및 채팅 정보 자동 저장 ---
            user = update.message.from_user
            chat = update.message.chat
            
            user_info = UserInfo(
                user_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name
            )
            chat_info = ChatInfo(
                chat_id=chat.id, chat_type=chat.type, title=chat.title, username=chat.username
            )
            storage.save_user(user_info)
            storage.save_chat(chat_info)
            logger.debug(f"Saved user {user.id} and chat {chat.id} info to DB.")
        
        # Process the update
        await telegram_app.process_update(update)
        
        return {"status": "ok"}
    
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "bot_running": telegram_app is not None,
        "config_loaded": config is not None,
        "total_messages": len(message_history),
        "active_users": len(set(msg["user_id"] for msg in message_history))
    }

@app.get("/messages", response_class=HTMLResponse)
async def view_messages(request: Request):
    """View recent messages in a web interface"""
    # DB에서 최근 메시지 조회
    from message_storage import MessageStorage
    message_storage = globals().get('message_storage')
    if not message_storage:
        message_storage = MessageStorage()
    # 최근 20개 메시지 (모든 채팅, 모든 사용자)
    recent_messages = []
    import sqlite3
    with message_storage._get_connection() as conn:
        cursor = conn.execute("SELECT * FROM messages ORDER BY timestamp DESC LIMIT 20")
        rows = cursor.fetchall()
        for row in rows:
            recent_messages.append({
                "user_id": row["user_id"],
                "username": "-",
                "first_name": "-",
                "timestamp": row["timestamp"],
                "message": row["content"]
            })

    context = {
        "request": request,
        "recent_messages": recent_messages,
        "total_messages": len(recent_messages),
        "active_users": len(set(msg["user_id"] for msg in recent_messages))
    }
    return templates.TemplateResponse("messages.html", context)

@app.get("/messages/json")
async def get_messages_json():
    """Get recent messages as JSON"""
    from services.message_service import MessageService
    message_service = globals().get('message_service')
    if not message_service:
        # message_storage가 이미 전역에 있다면 활용
        message_storage = globals().get('message_storage')
        if not message_storage:
            from message_storage import MessageStorage
            message_storage = MessageStorage()
        message_service = MessageService(message_storage)
    recent_messages = message_service.get_all_messages(limit=20)
    return {
        "total_messages": len(recent_messages),
        "active_users": len(set(msg["user_id"] for msg in recent_messages)),
        "recent_messages": recent_messages
    }

@app.get("/webhook/info")
async def webhook_info():
    """Get current webhook information"""
    try:
        webhook_info = await telegram_app.bot.get_webhook_info()
        return {
            "webhook_url": webhook_info.url,
            "has_custom_certificate": webhook_info.has_custom_certificate,
            "pending_update_count": webhook_info.pending_update_count,
            "last_error_date": webhook_info.last_error_date.isoformat() if webhook_info.last_error_date else None,
            "last_error_message": webhook_info.last_error_message,
            "max_connections": webhook_info.max_connections,
            "allowed_updates": webhook_info.allowed_updates,
            "last_synchronization_error_date": webhook_info.last_synchronization_error_date.isoformat() if webhook_info.last_synchronization_error_date else None
        }
    except Exception as e:
        logger.error(f"Error getting webhook info: {str(e)}")
        return {"error": str(e)}

@app.post("/webhook/test")
async def test_webhook():
    """Test webhook by sending a test message to the bot"""
    try:
        # This is mainly for documentation - actual testing should be done via Telegram
        return {
            "message": "webhook 테스트는 Telegram 앱에서 봇에게 메시지를 보내서 확인하세요",
            "test_endpoints": [
                "GET /webhook/info - Webhook 정보 확인",
                "GET /messages - 실시간 메시지 모니터링", 
                "GET /health - 봇 상태 확인"
            ]
        }
    except Exception as e:
        return {"error": str(e)}

@app.delete("/webhook")
async def delete_webhook():
    """Delete current webhook (for testing purposes)"""
    try:
        result = await telegram_app.bot.delete_webhook()
        return {"success": result, "message": "Webhook deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting webhook: {str(e)}")
        return {"error": str(e)}

@app.post("/webhook/set")
async def set_webhook():
    """Manually set webhook (useful for debugging)"""
    try:
        webhook_url = f"{config['telegram']['webhook_url']}{config['telegram']['webhook_path']}"
        result = await telegram_app.bot.set_webhook(webhook_url)
        return {
            "success": result,
            "webhook_url": webhook_url,
            "message": "Webhook set successfully"
        }
    except Exception as e:
        logger.error(f"Error setting webhook: {str(e)}")
        return {"error": str(e)}

@app.get("/dashboard", response_class=HTMLResponse)
async def webhook_dashboard(request: Request):
    """Webhook status dashboard"""
    try:
        webhook_info = await telegram_app.bot.get_webhook_info()
        webhook_status = "✅ 활성" if webhook_info.url else "❌ 비활성"
        
        # DB에서 통계 및 최근 메시지 가져오기
        from message_storage import MessageStorage
        storage = MessageStorage()
        db_stats = storage.get_database_stats()
        
        # search_messages는 최신순으로 반환합니다.
        recent_messages_from_db = storage.search_messages(query="%", limit=20)

        context = {
            "request": request,
            "webhook_info": webhook_info,
            "webhook_status": webhook_status,
            "db_stats": db_stats,
            "recent_messages": recent_messages_from_db,
            # 메모리 기반 활성 사용자 대신 DB 기반 총 사용자 수 사용
            "active_users": db_stats.get("users_count", 0) 
        }
        return templates.TemplateResponse("dashboard.html", context)
    except Exception as e:
        return HTMLResponse(content=f"<html><body><h1>오류</h1><p>Dashboard 로딩 중 오류: {str(e)}</p></body></html>")

@app.post("/admin/reset-db")
async def reset_database():
    """
    데이터베이스를 초기화합니다. (주의: 모든 데이터 삭제)
    """
    try:
        from message_storage import MessageStorage
        storage = MessageStorage()
        storage.reset_database()
        return {"status": "ok", "message": "데이터베이스가 성공적으로 초기화되었습니다."}
    except Exception as e:
        logger.error(f"Error resetting database: {str(e)}")
        raise HTTPException(status_code=500, detail=f"데이터베이스 초기화 중 오류 발생: {e}")

@app.get("/stats")
async def get_stats():
    """Get bot statistics"""
    if not message_history:
        return {"total_messages": 0, "active_users": 0, "user_stats": []}
    
    # Count messages per user
    user_stats = {}
    for msg in message_history:
        user_id = msg["user_id"]
        if user_id not in user_stats:
            user_stats[user_id] = {
                "name": msg["first_name"],
                "username": msg["username"],
                "message_count": 0
            }
        user_stats[user_id]["message_count"] += 1
    
    return {
        "total_messages": len(message_history),
        "active_users": len(user_stats),
        "user_stats": list(user_stats.values())
    }

if __name__ == "__main__":
    
    # Load config for development
    config = load_config()
    setup_logging(config)
    
    print("🤖 Starting Telegram Gemini Bot...")
    print(f"📍 Host: {config['telegram']['host']}")
    print(f"🔌 Port: {config['telegram']['port']}")
    print(f"🤖 Model: {config['gemini']['model_name']}")
    
    uvicorn.run(
        "main:app",
        host=config["telegram"]["host"],
        port=config["telegram"]["port"],
        reload=config["app"]["debug"],
        log_level=config["app"]["log_level"].lower()
    )