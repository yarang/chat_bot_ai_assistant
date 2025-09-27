"""
Telegram Bot with Gemini AI - Main FastAPI Application
"""
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
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
        "config_loaded": config is not None
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
        "__main__:app",
        host=config["telegram"]["host"],
        port=config["telegram"]["port"],
        reload=config["app"]["debug"],
        log_level=config["app"]["log_level"].lower()
    )