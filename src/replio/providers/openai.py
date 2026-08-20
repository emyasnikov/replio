from .base import OpenAICompatibleProvider


class OpenAIProvider(OpenAICompatibleProvider):
    DEFAULT_BASE_URL = 'https://api.openai.com/v1'
    DEFAULT_MODEL = 'gpt-4o-mini'

    def _reasoning_payload(self, payload: dict) -> dict:
        if self._reasoning_off(self.reasoning):
            return payload
        effort = self.reasoning
        if effort is True or effort in ('on', 'auto', 'medium'):
            effort = 'medium'
        if effort in ('low', 'medium', 'high'):
            payload['reasoning_effort'] = effort
        return payload
