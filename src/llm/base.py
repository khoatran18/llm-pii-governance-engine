from abc import ABC, abstractmethod

class BaseLLMProvider(ABC):
    def __init__(self, config: dict):
        self.config = config
        self.llm_config = config.get("llm", {})
        self.model = self.llm_config["model"]
        self.temperature = self.llm_config["temperature"]
        self.max_tokens = self.llm_config["max_tokens"]

    @abstractmethod
    def get_response(self, prompt: str, **kwargs) -> str:
        """
        Get response from LLM provider
        """
        pass