from openai import OpenAI
from openai.types.chat import ChatCompletionUserMessageParam

from base import BaseLLMProvider

class OpenAIProvider(BaseLLMProvider):
    def __init__(self, config):
        super().__init__(config)
        self.client = OpenAI(api_key=self.api_key)

    def get_response(self, prompt: str, **kwargs) -> str:
        messages: list[ChatCompletionUserMessageParam] = [
            {"role": "user", "content": prompt}
        ]
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        return response.choices[0].message.content

class DeepSeekProvider(BaseLLMProvider):
    def __init__(self, config, base_url: str = "https://api.deepseek.com/v1"):
        super().__init__(config)
        self.base_url = base_url
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def get_response(self, prompt: str, **kwargs) -> str:
        messages: list[ChatCompletionUserMessageParam] = [
            {"role": "user", "content": prompt}
        ]
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        return response.choices[0].message.content

