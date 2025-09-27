"""
Google Gemini API Client for Telegram Bot
"""
import logging
from typing import Optional, Dict, Any, List
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

logger = logging.getLogger(__name__)

class GeminiClient:
    """Client for interacting with Google Gemini API"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Gemini client
        
        Args:
            config: Gemini configuration dictionary
        """
        self.config = config
        self.api_key = config["api_key"]
        self.model_name = config.get("model_name", "gemini-1.5-flash")
        self.temperature = config.get("temperature", 0.7)
        self.max_tokens = config.get("max_tokens", 1000)
        self.top_p = config.get("top_p", 0.8)
        self.top_k = config.get("top_k", 40)
        
        # Configure API
        genai.configure(api_key=self.api_key)
        
        # Initialize model
        self.model = self._initialize_model()
        
        # Conversation history storage (simple in-memory)
        self.conversations: Dict[int, List[Dict[str, str]]] = {}
        
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
        user_id: int, 
        message: str, 
        maintain_context: bool = True
    ) -> str:
        """
        Generate response from Gemini
        
        Args:
            user_id: Telegram user ID for context management
            message: User message
            maintain_context: Whether to maintain conversation context
            
        Returns:
            Generated response string
            
        Raises:
            Exception: If API call fails
        """
        try:
            if maintain_context:
                # Get or create conversation history
                if user_id not in self.conversations:
                    self.conversations[user_id] = []
                
                conversation = self.conversations[user_id]
                
                # Build conversation context
                context_messages = []
                for msg in conversation[-10:]:  # Keep last 10 messages for context
                    context_messages.append(f"User: {msg['user']}")
                    context_messages.append(f"Assistant: {msg['assistant']}")
                
                # Add current message
                context_messages.append(f"User: {message}")
                
                # Create prompt with context
                prompt = "\n".join(context_messages)
            else:
                prompt = message
            
            # Generate response
            response = self.model.generate_content(prompt)
            
            if response.text:
                response_text = response.text.strip()
                
                # Save to conversation history if maintaining context
                if maintain_context:
                    self.conversations[user_id].append({
                        "user": message,
                        "assistant": response_text
                    })
                    
                    # Limit conversation history size
                    if len(self.conversations[user_id]) > 20:
                        self.conversations[user_id] = self.conversations[user_id][-15:]
                
                logger.info(f"Generated response for user {user_id}")
                return response_text
            else:
                logger.warning(f"Empty response from Gemini for user {user_id}")
                return "죄송합니다. 응답을 생성할 수 없습니다."
                
        except Exception as e:
            logger.error(f"Error generating response for user {user_id}: {str(e)}")
            return f"오류가 발생했습니다: {str(e)}"
    
    def clear_conversation(self, user_id: int) -> None:
        """
        Clear conversation history for a user
        
        Args:
            user_id: Telegram user ID
        """
        if user_id in self.conversations:
            del self.conversations[user_id]
            logger.info(f"Cleared conversation history for user {user_id}")
    
    def get_conversation_length(self, user_id: int) -> int:
        """
        Get the length of conversation history for a user
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Number of message pairs in conversation
        """
        return len(self.conversations.get(user_id, []))
    
    def set_model_parameters(
        self, 
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None
    ) -> None:
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
        Get current model information
        
        Returns:
            Dictionary with model configuration
        """
        return {
            "model_name": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "active_conversations": len(self.conversations)
        }