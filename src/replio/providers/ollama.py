from .base import OpenAICompatibleProvider


class OllamaProvider(OpenAICompatibleProvider):
    DEFAULT_BASE_URL = 'https://api.ollama.com'
    DEFAULT_MODEL = 'llama3.2'
