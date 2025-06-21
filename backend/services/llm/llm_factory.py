"""LLM factory for creating language model instances."""

import logging
from typing import Dict, Any

from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema.language_model import BaseLanguageModel

from config import get_settings

logger = logging.getLogger(__name__)


class LLMFactory:
    """Factory for creating language model instances."""
    
    def __init__(self):
        self.settings = get_settings()
        self._models: Dict[str, BaseLanguageModel] = {}
    
    def get_chat_model(self, model_name: str = None) -> BaseLanguageModel:
        """Get a chat model instance."""
        if model_name is None:
            model_name = self.settings.llm_model_mistral
        
        # Return cached model if available
        if model_name in self._models:
            return self._models[model_name]
        
        # Create new model based on provider
        if self.settings.llm_provider == "ollama":
            model = self._create_ollama_chat_model(model_name)
        elif self.settings.llm_provider == "gemini":
            model = self._create_gemini_chat_model(model_name)
        else:
            raise ValueError(f"Unsupported LLM provider: {self.settings.llm_provider}")
        
        # Cache and return
        self._models[model_name] = model
        logger.info(f"Created chat model: {model_name} using {self.settings.llm_provider}")
        return model
    
    def get_risk_model(self) -> BaseLanguageModel:
        """Get the risk classification model."""
        return self.get_chat_model(self.settings.llm_model_risk)
    
    def _create_ollama_chat_model(self, model_name: str) -> ChatOllama:
        """Create an Ollama chat model."""
        return ChatOllama(
            model=model_name,
            base_url=self.settings.ollama_base_url,
            temperature=0.1,  # Low temperature for consistent outputs
            num_predict=2048,  # Max tokens
            top_k=40,
            top_p=0.9,
            repeat_penalty=1.1,
            verbose=self.settings.debug
        )
    
    def _create_gemini_chat_model(self, model_name: str) -> ChatGoogleGenerativeAI:
        """Create a Gemini chat model."""
        if not self.settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required for Gemini provider")
        
        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=self.settings.gemini_api_key,
            temperature=0.1,  # Low temperature for consistent outputs
            max_tokens=2048,  # Max tokens
            top_p=0.9,
            verbose=self.settings.debug,
            # Safety settings for therapy use case
            safety_settings={
                "HARM_CATEGORY_HARASSMENT": "BLOCK_MEDIUM_AND_ABOVE",
                "HARM_CATEGORY_HATE_SPEECH": "BLOCK_MEDIUM_AND_ABOVE",
                "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_MEDIUM_AND_ABOVE",
                "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_MEDIUM_AND_ABOVE",
            }
        )
    
    def clear_cache(self):
        """Clear the model cache."""
        self._models.clear()
        logger.info("Model cache cleared")
    
    def list_cached_models(self) -> list[str]:
        """List currently cached models."""
        return list(self._models.keys())


# Global factory instance
_llm_factory = LLMFactory()


def get_chat_model(model_name: str = None) -> BaseLanguageModel:
    """Get a chat model instance."""
    return _llm_factory.get_chat_model(model_name)


def get_risk_model() -> BaseLanguageModel:
    """Get the risk classification model."""
    return _llm_factory.get_risk_model()


def clear_model_cache():
    """Clear the model cache."""
    _llm_factory.clear_cache()


def list_cached_models() -> list[str]:
    """List currently cached models."""
    return _llm_factory.list_cached_models()