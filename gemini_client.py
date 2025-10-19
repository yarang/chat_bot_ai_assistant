"""
Google Gemini API Client for Telegram Bot with SQLite Storage
"""

from __future__ import annotations

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from models import Message
from message_storage import MessageStorage
from repositories import ChatRepository
from services.chat_service import ChatService

logger = logging.getLogger(__name__)


class GeminiClient:
    """Client for interacting with Google Gemini API with persistent storage"""

    def __init__(
        self, config: Dict[str, Any], storage: Optional[MessageStorage] = None
    ):
        """
        Initialize Gemini client

        Args:
            config: Gemini configuration dictionary
            storage: MessageStorage instance (creates new if None)
        """
        self.config = config
        self.api_key = config["api_key"]
        self.model_name = config.get("model_name", "gemini-pro")
        self.temperature = config.get("temperature", 0.7)
        self.max_tokens = config.get("max_tokens", 1000)
        self.top_p = config.get("top_p", 0.8)
        self.top_k = config.get("top_k", 40)

        # Initialize storage and services
        self.storage = storage or MessageStorage()
        self.chat_repository = ChatRepository(self.storage)
        self.chat_service = ChatService(self.chat_repository)

        # Configure API
        genai.configure(api_key=self.api_key)

        # Check available models and validate
        self._validate_model()

        # Initialize model
        self.model = self._initialize_model()

    def _validate_model(self):
        """Validate and potentially fix model name"""
        try:
            # List available models
            available_models = []
            for model in genai.list_models():
                if "generateContent" in model.supported_generation_methods:
                    available_models.append(model.name.replace("models/", ""))

            logger.info(f"Available models: {available_models}")

            # Check if current model is available
            if self.model_name not in available_models:
                logger.warning(
                    f"Model '{self.model_name}' not available. Available models: {available_models}"
                )

                # Try common model names in order of preference
                fallback_models = [
                    "gemini-pro",
                    "gemini-1.5-pro",
                    "gemini-1.0-pro",
                    "gemini-pro-vision",
                ]

                for fallback in fallback_models:
                    if fallback in available_models:
                        logger.info(f"Using fallback model: {fallback}")
                        self.model_name = fallback
                        return

                # If no fallback works, use first available model
                if available_models:
                    self.model_name = available_models[0]
                    logger.info(f"Using first available model: {self.model_name}")
                else:
                    raise ValueError("No suitable models available")
            else:
                logger.info(f"Using model: {self.model_name}")

        except Exception as e:
            logger.error(f"Error validating model: {str(e)}")
            # Default to gemini-pro as last resort
            self.model_name = "gemini-pro"
            logger.info(f"Falling back to default model: {self.model_name}")

    def get_available_models(self) -> List[str]:
        """Get list of available models"""
        try:
            models = []
            for model in genai.list_models():
                if "generateContent" in model.supported_generation_methods:
                    models.append(model.name.replace("models/", ""))
            return models
        except Exception as e:
            logger.error(f"Error getting available models: {str(e)}")
            return []

    def _initialize_model(self):
        """Initialize the Gemini model with safety settings"""

        generation_config = {
            "temperature": self.temperature,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "max_output_tokens": self.max_tokens,
        }

        safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        }

        try:
            model = genai.GenerativeModel(
                model_name=self.model_name,
                generation_config=generation_config,
                safety_settings=safety_settings,
            )
            logger.info(f"Gemini model '{self.model_name}' initialized successfully")
            return model
        except Exception as e:
            logger.error(f"Failed to initialize Gemini model: {str(e)}")
            raise

    async def generate_response(
        self,
        chat_id: int,
        user_id: int,
        message: str,
        maintain_context: bool = True,
        context_length: int = 10,
    ):
        """
        Generate response from Gemini with persistent storage, using ChatSession and streaming.

        Args:
            chat_id: Telegram chat ID
            user_id: Telegram user ID for context management
            message: User message
            maintain_context: Whether to maintain conversation context
            context_length: Number of previous messages to include in context

        Yields:
            Generated response string chunks
        """
        logger.info(
            f"Generating response for user {user_id} in chat {chat_id}. "
            f"Context: {'On' if maintain_context else 'Off'} "
            f"(length: {context_length if maintain_context else 0})"
        )

        interaction_id = uuid.uuid4().hex

        try:
            # 1. Save user message first
            user_message = Message(
                chat_id=chat_id, user_id=user_id, role="user", content=message, timestamp=datetime.now()
            )
            setattr(user_message, 'interaction_id', interaction_id)
            self.storage.save_message(user_message)

            # 2. Build history for ChatSession
            api_history = []
            persona_prompt = self.chat_service.get_persona(chat_id)

            if maintain_context:
                db_history = self.storage.get_conversation_history(
                    chat_id=chat_id, limit=context_length * 2, include_system=True
                )
                for msg in db_history:
                    api_history.append({
                        'role': 'model' if msg.role == 'assistant' else 'user', 
                        'parts': [msg.content]
                    })
            
            # 3. Start chat session and prepare the message to send
            chat_session = self.model.start_chat(history=api_history)
            
            # Inject persona into the first turn if it exists
            message_to_send = message
            if persona_prompt and not api_history:
                message_to_send = f"{persona_prompt}\n\nUser: {message}"
                logger.debug("Persona prompt injected into the first message.")

            # 4. Generate response using streaming
            response_stream = chat_session.send_message(message_to_send, stream=True)

            finish_reason = None
            full_response_text = ""
            for chunk in response_stream:
                if chunk.text:
                    yield chunk.text
                    full_response_text += chunk.text
                finish_reason = chunk.candidates[0].finish_reason.name if chunk.candidates else None

            # 5. Save the full response to the database at the end
            response_text = full_response_text.strip()
            if response_text:
                assistant_message = Message(
                    chat_id=chat_id, user_id=user_id, role="assistant", content=response_text,
                    timestamp=datetime.now(),
                    metadata={"model": self.model_name, "temperature": self.temperature, "context_used": maintain_context}
                )
                setattr(assistant_message, 'interaction_id', interaction_id)
                self.storage.save_message(assistant_message)
                logger.info(f"Finished generating and saving full response for user {user_id} in chat {chat_id}")
            else:
                logger.warning(f"Empty final response from Gemini for user {user_id} in chat {chat_id}")

            # 6. Note about token counting
            logger.warning("Token usage metadata is not available for streaming responses and was not recorded.")

            # 7. Yield finish reason at the end
            yield {"finish_reason": finish_reason, "full_response_text": full_response_text}

        except StopIteration:
            logger.warning(f"Caught StopIteration for user {user_id} in chat {chat_id}, likely an empty response from the model.")
            yield "모델로부터 응답이 없습니다. 다른 질문을 시도해 주세요."
        except Exception as e:
            logger.exception(f"Error generating response for user {user_id} in chat {chat_id}: {str(e)}")
            yield f"오류가 발생했습니다: {str(e)}"

    def clear_conversation(self, chat_id: int, user_id: int) -> int:
        """
        Clear conversation history (marks messages as deleted or removes them)

        Args:
            chat_id: Telegram chat ID
            user_id: Specific user ID (None for all users in chat)

        Returns:
            Number of messages cleared
        """
        logger.info(f"Clearing conversation for user {user_id} in chat {chat_id}.")
        try:
            cleared_count = self.storage.clear_conversation(chat_id=chat_id, user_id=user_id)
            logger.info(
                f"Successfully cleared {cleared_count} messages for user {user_id} in chat {chat_id}."
            )
            return cleared_count
        except Exception as e:
            logger.error(f"Error clearing conversation: {str(e)}")
            return 0

    def get_conversation_length(
        self, chat_id: int, user_id: Optional[int] = None
    ) -> int:
        """
        Get the length of conversation history

        Args:
            chat_id: Telegram chat ID
            user_id: Specific user ID (None for all users in chat)

        Returns:
            Number of messages in conversation
        """
        try:
            history = self.storage.get_conversation_history(
                chat_id, user_id, limit=1000
            )
            return len(history)
        except Exception as e:
            logger.error(f"Error getting conversation length: {str(e)}")
            return 0

    def get_chat_statistics(self, chat_id: int) -> Dict[str, Any]:
        """
        Get comprehensive chat statistics

        Args:
            chat_id: Telegram chat ID

        Returns:
            Dictionary with chat statistics
        """
        try:
            return self.storage.get_chat_stats(chat_id)
        except Exception as e:
            logger.error(f"Error getting chat statistics: {str(e)}")
            return {}

    def get_user_statistics(self, user_id: int) -> Dict[str, Any]:
        """
        Get comprehensive user statistics

        Args:
            user_id: Telegram user ID

        Returns:
            Dictionary with user statistics
        """
        try:
            return self.storage.get_user_stats(user_id)
        except Exception as e:
            logger.error(f"Error getting user statistics: {str(e)}")
            return {}

    def get_user_token_statistics(self, user_id: int) -> Dict[str, Any]:
        """사용자별 토큰 통계 반환 (storage passthrough)"""
        try:
            return self.storage.get_user_token_stats(user_id)
        except Exception as e:
            logger.error(f"Error getting user token stats: {str(e)}")
            return {}

    def search_messages(
        self, query: str, chat_id: Optional[int] = None, user_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Search messages by content

        Args:
            query: Search query
            chat_id: Limit search to specific chat
            user_id: Limit search to specific user

        Returns:
            List of matching messages
        """
        try:
            messages = self.storage.search_messages(query, chat_id, user_id)
            return [
                {
                    "chat_id": msg.chat_id,
                    "user_id": msg.user_id,
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "metadata": msg.metadata,
                }
                for msg in messages
            ]
        except Exception as e:
            logger.error(f"Error searching messages: {str(e)}")
            return []

    def set_model_parameters(
        self,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
    ) -> None:
        logger.info(
            f"Updating model parameters: temp={temperature}, "
            f"max_tokens={max_tokens}, top_p={top_p}, top_k={top_k}"
        )

        """
        Update model parameters

        Args:
            temperature: Randomness of responses (0.0-1.0)
            max_tokens: Maximum tokens in response
            top_p: Nucleus sampling parameter
            top_k: Top-k sampling parameter
        """
        if temperature is not None:
            self.temperature = temperature
        if max_tokens is not None:
            self.max_tokens = max_tokens
        if top_p is not None:
            self.top_p = top_p
        if top_k is not None:
            self.top_k = top_k

        # Reinitialize model with new parameters
        self.model = self._initialize_model()
        logger.info("Model parameters updated")

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get current model information including storage stats

        Returns:
            Dictionary with model configuration and storage statistics
        """
        logger.info("Fetching model information and storage stats.")
        model_info = {
            "model_name": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "top_k": self.top_k,
        }

        # Add storage statistics
        try:
            storage_stats = self.storage.get_database_stats()
            model_info.update(
                {
                    "storage_stats": storage_stats,
                    "total_conversations": storage_stats.get("chats_count", 0),
                    "total_messages": storage_stats.get("messages_count", 0),
                    "total_users": storage_stats.get("users_count", 0),
                }
            )
        except Exception as e:
            logger.error(f"Error getting storage stats: {str(e)}")
            model_info["storage_error"] = str(e)

        return model_info

    def export_conversation(self, chat_id: int, format: str = "json") -> str:
        """
        Export conversation history

        Args:
            chat_id: Chat ID to export
            format: Export format ('json' or 'txt')

        Returns:
            Exported conversation data
        """
        try:
            return self.storage.export_chat_history(chat_id, format)
        except Exception as e:
            logger.error(f"Error exporting conversation: {str(e)}")
            return f"Export failed: {str(e)}"

    def cleanup_old_data(self, days_to_keep: int = 30) -> Dict[str, int]:
        """
        Clean up old conversation data

        Args:
            days_to_keep: Number of days to keep

        Returns:
            Cleanup statistics
        """
        try:
            deleted_messages = self.storage.cleanup_old_messages(days_to_keep)
            return {"deleted_messages": deleted_messages, "days_kept": days_to_keep}
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
            return {"error": str(e)}

    def close(self):
        """Close storage connection and cleanup resources"""
        if hasattr(self, "storage"):
            self.storage.close()
        logger.info("GeminiClient closed")
