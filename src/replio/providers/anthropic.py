from .base import OpenAICompatibleProvider


class AnthropicProvider(OpenAICompatibleProvider):
    DEFAULT_BASE_URL = 'https://api.anthropic.com/v1'
    DEFAULT_MODEL = 'claude-sonnet-4-20250514'
