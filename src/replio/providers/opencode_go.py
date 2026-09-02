from .base import OpenAICompatibleProvider


class OpenCodeGoProvider(OpenAICompatibleProvider):
    DEFAULT_BASE_URL = 'https://opencode.ai/zen/go/v1'
    DEFAULT_MODEL = 'deepseek-v4-flash'

    def _payload(self, messages, stream=False, tools=None):
        payload = super()._payload(messages, stream=stream, tools=tools)
        model = self.model
        if model.startswith('opencode-go/'):
            payload['model'] = model[len('opencode-go/'):]
        return payload