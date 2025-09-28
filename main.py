"""
Telegram Bot with Gemini AI - Main FastAPI Application
"""
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from telegram import Update
from telegram.ext import Application

from bot import setup_bot_handlers
from config_loader import load_config

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Global variables
telegram_app = None
config = None
message_history = []  # Store recent messages for monitoring

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan"""
    global telegram_app, config
    
    # Startup
    config = load_config()
    telegram_app = setup_telegram_app()
    
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

def setup_telegram_app():
    """Setup Telegram application with handlers"""
    app = Application.builder().token(config["telegram"]["bot_token"]).build()
    setup_bot_handlers(app, config)
    return app

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
        update = Update.de_json(update_data, telegram_app.bot)
        
        # Store message for monitoring (keep last 100 messages)
        if update.message:
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
async def view_messages():
    """View recent messages in a web interface"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Telegram Bot Messages</title>
        <meta charset="UTF-8">
        <meta http-equiv="refresh" content="10">
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
            .header { background-color: #0088cc; color: white; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
            .message { background-color: white; border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px; }
            .user-info { font-weight: bold; color: #0088cc; }
            .timestamp { color: #666; font-size: 0.9em; }
            .message-text { margin: 10px 0; padding: 10px; background-color: #f9f9f9; border-left: 3px solid #0088cc; }
            .stats { background-color: #e8f4f8; padding: 10px; border-radius: 5px; margin-bottom: 20px; }
            .no-messages { text-align: center; color: #666; padding: 50px; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🤖 Telegram Bot Message Monitor</h1>
            <p>실시간 메시지 모니터링 (10초마다 자동 새로고침)</p>
        </div>
        
        <div class="stats">
            <strong>📊 통계:</strong> 
            총 메시지: """ + str(len(message_history)) + """개 | 
            활성 사용자: """ + str(len(set(msg["user_id"] for msg in message_history))) + """명
        </div>
    """
    
    if not message_history:
        html_content += '<div class="no-messages">아직 메시지가 없습니다.</div>'
    else:
        # Show latest messages first
        for msg in reversed(message_history[-20:]):  # Show last 20 messages
            html_content += f"""
            <div class="message">
                <div class="user-info">
                    👤 {msg['first_name']} (@{msg['username']}) - ID: {msg['user_id']}
                </div>
                <div class="timestamp">
                    🕒 {msg['timestamp']}
                </div>
                <div class="message-text">
                    💬 {msg['message']}
                </div>
            </div>
            """
    
    html_content += """
        </body>
    </html>
    """
    return html_content

@app.get("/messages/json")
async def get_messages_json():
    """Get recent messages as JSON"""
    return {
        "total_messages": len(message_history),
        "active_users": len(set(msg["user_id"] for msg in message_history)),
        "recent_messages": message_history[-20:] if message_history else []
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
async def webhook_dashboard():
    """Webhook status dashboard"""
    try:
        webhook_info = await telegram_app.bot.get_webhook_info()
        webhook_status = "✅ 활성" if webhook_info.url else "❌ 비활성"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Telegram Bot Dashboard</title>
            <meta charset="UTF-8">
            <meta http-equiv="refresh" content="30">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
                .header {{ background-color: #0088cc; color: white; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                .card {{ background-color: white; border: 1px solid #ddd; margin: 10px 0; padding: 20px; border-radius: 5px; }}
                .status-good {{ color: #28a745; font-weight: bold; }}
                .status-bad {{ color: #dc3545; font-weight: bold; }}
                .status-warning {{ color: #ffc107; font-weight: bold; }}
                .info-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 20px 0; }}
                .btn {{ background-color: #0088cc; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin: 5px; display: inline-block; }}
                .btn:hover {{ background-color: #0066aa; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background-color: #f8f9fa; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🤖 Telegram Bot Dashboard</h1>
                <p>봇 상태 및 Webhook 모니터링 (30초마다 자동 새로고침)</p>
            </div>
            
            <div class="info-grid">
                <div class="card">
                    <h3>📡 Webhook 상태</h3>
                    <p><strong>상태:</strong> <span class="{'status-good' if webhook_info.url else 'status-bad'}">{webhook_status}</span></p>
                    <p><strong>URL:</strong> {webhook_info.url or '설정되지 않음'}</p>
                    <p><strong>대기 중인 업데이트:</strong> {webhook_info.pending_update_count}개</p>
                    {'<p><strong>마지막 오류:</strong> <span class="status-bad">' + str(webhook_info.last_error_message) + '</span></p>' if webhook_info.last_error_message else '<p><strong>오류:</strong> <span class="status-good">없음</span></p>'}
                </div>
                
                <div class="card">
                    <h3>📊 봇 통계</h3>
                    <p><strong>총 메시지:</strong> {len(message_history)}개</p>
                    <p><strong>활성 사용자:</strong> {len(set(msg["user_id"] for msg in message_history))}명</p>
                    <p><strong>봇 실행 상태:</strong> <span class="status-good">✅ 정상</span></p>
                </div>
            </div>
            
            <div class="card">
                <h3>🔧 관리 도구</h3>
                <a href="/webhook/info" class="btn">Webhook 정보 (JSON)</a>
                <a href="/messages" class="btn">실시간 메시지</a>
                <a href="/stats" class="btn">통계 (JSON)</a>
                <a href="/health" class="btn">상태 확인</a>
            </div>
            
            <div class="card">
                <h3>📋 Webhook 상세 정보</h3>
                <table>
                    <tr><th>항목</th><th>값</th></tr>
                    <tr><td>Webhook URL</td><td>{webhook_info.url or '없음'}</td></tr>
                    <tr><td>사용자 정의 인증서</td><td>{'예' if webhook_info.has_custom_certificate else '아니오'}</td></tr>
                    <tr><td>최대 연결 수</td><td>{webhook_info.max_connections}</td></tr>
                    <tr><td>허용된 업데이트</td><td>{', '.join(webhook_info.allowed_updates) if webhook_info.allowed_updates else '모든 업데이트'}</td></tr>
                    <tr><td>마지막 오류 시간</td><td>{webhook_info.last_error_date.strftime('%Y-%m-%d %H:%M:%S') if webhook_info.last_error_date else '없음'}</td></tr>
                </table>
            </div>
            
        </body>
        </html>
        """
        return html_content
    except Exception as e:
        return f"<html><body><h1>오류</h1><p>Dashboard 로딩 중 오류: {str(e)}</p></body></html>"

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
    import uvicorn
    
    # Load config for development
    config = load_config()
    
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