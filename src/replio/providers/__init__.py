from .base import OpenAICompatibleProvider
from .ollama import OllamaProvider
from .openai import OpenAIProvider
from .groq import GroqProvider
from .anthropic import AnthropicProvider

PROVIDERS = {
    'ollama': OllamaProvider,
    'openai': OpenAIProvider,
    'groq': GroqProvider,
    'anthropic': AnthropicProvider,
    'openai-compatible': OpenAICompatibleProvider,
}


def detect_provider(base_url: str = '') -> str:
    host = (base_url or '').lower()
    if 'openai.com' in host:
        return 'openai'
    if 'groq.com' in host:
        return 'groq'
    if 'anthropic.com' in host:
        return 'anthropic'
    if 'ollama.com' in host or 'ollama.ai' in host:
        return 'ollama'
    return 'openai-compatible'


__all__ = ['PROVIDERS', 'detect_provider', 'OpenAICompatibleProvider',
           'OllamaProvider', 'OpenAIProvider', 'GroqProvider', 'AnthropicProvider']
