from .base import OpenAICompatibleProvider


class OpenCodeProvider(OpenAICompatibleProvider):
    DEFAULT_BASE_URL = 'https://opencode.ai/zen/v1'
    DEFAULT_MODEL = 'kimi-k3'

    def _payload(self, messages, stream=False, tools=None):
        payload = super()._payload(messages, stream=stream, tools=tools)
        model = self.model
        if model.startswith('opencode/'):
            payload['model'] = model[len('opencode/'):]
        return payload