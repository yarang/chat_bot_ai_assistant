"""
Configuration loader for Telegram Gemini Bot
"""
import json
import os
from typing import Dict, Any

def load_config(config_path: str = "config.json") -> Dict[str, Any]:
    """
    Load configuration from JSON file with environment variable overrides
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Configuration dictionary
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        json.JSONDecodeError: If config file is invalid JSON
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"Invalid JSON in config file: {str(e)}")
    
    # Override with environment variables if they exist
    config = _override_with_env_vars(config)
    
    # Validate required fields
    _validate_config(config)
    
    return config

def _override_with_env_vars(config: Dict[str, Any]) -> Dict[str, Any]:
    """Override config values with environment variables"""
    
    # Telegram settings
    if "TELEGRAM_BOT_TOKEN" in os.environ:
        config["telegram"]["bot_token"] = os.environ["TELEGRAM_BOT_TOKEN"]
    
    if "TELEGRAM_WEBHOOK_URL" in os.environ:
        config["telegram"]["webhook_url"] = os.environ["TELEGRAM_WEBHOOK_URL"]
    
    if "PORT" in os.environ:
        config["telegram"]["port"] = int(os.environ["PORT"])
    
    if "HOST" in os.environ:
        config["telegram"]["host"] = os.environ["HOST"]
    
    # Gemini settings
    if "GEMINI_API_KEY" in os.environ:
        config["gemini"]["api_key"] = os.environ["GEMINI_API_KEY"]
    
    if "GEMINI_MODEL" in os.environ:
        config["gemini"]["model_name"] = os.environ["GEMINI_MODEL"]
    
    # App settings
    if "DEBUG" in os.environ:
        config["app"]["debug"] = os.environ["DEBUG"].lower() in ("true", "1", "yes")
    
    if "LOG_LEVEL" in os.environ:
        config["app"]["log_level"] = os.environ["LOG_LEVEL"].upper()
    
    return config

def _validate_config(config: Dict[str, Any]) -> None:
    """Validate that required configuration fields are present"""
    
    required_fields = [
        ("telegram", "bot_token"),
        ("gemini", "api_key"),
    ]
    
    for section, field in required_fields:
        if section not in config:
            raise ValueError(f"Missing required config section: {section}")
        
        if field not in config[section]:
            raise ValueError(f"Missing required config field: {section}.{field}")
        
        if not config[section][field] or config[section][field].startswith("YOUR_"):
            raise ValueError(f"Please set a valid value for {section}.{field} in config.json or environment variables")

def get_telegram_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Get Telegram-specific configuration"""
    return config.get("telegram", {})

def get_gemini_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Get Gemini-specific configuration"""
    return config.get("gemini", {})

def get_app_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Get application-specific configuration"""
    return config.get("app", {})