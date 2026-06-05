import logging

from src.config.logging import setup_logging
from src.llm.base import BaseLLMProvider
from src.llm.providers import OpenAIProvider, DeepSeekProvider

setup_logging()
logger = logging.getLogger(__name__)

class LLMFactory:
    @staticmethod
    def get_llm_provider(config: dict) -> BaseLLMProvider:
        """
        LLMFactory is a factory class that returns an instance of the LLMProvider class
        """
        llm_config = config.get("llm", {})
        provider_name = llm_config.get("provider", "openai")

        if provider_name == "openai":
            logger.info("Using OpenAIProvider ...")
            return OpenAIProvider(config)
        elif provider_name == "deepseek":
            logger.info("Using DeepSeekProvider ...")
            return DeepSeekProvider(config)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider_name}")