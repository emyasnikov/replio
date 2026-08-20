from .base import OpenAICompatibleProvider


class AnthropicProvider(OpenAICompatibleProvider):
    DEFAULT_BASE_URL = 'https://api.anthropic.com/v1'
    DEFAULT_MODEL = 'claude-sonnet-4-20250514'

    _BUDGET = {'low': 1024, 'medium': 2048, 'high': 4096}

    def _reasoning_payload(self, payload: dict) -> dict:
        if self._reasoning_off(self.reasoning):
            payload['thinking'] = {'type': 'disabled'}
            return payload
        effort = self.reasoning
        if effort is True or effort in ('on', 'auto'):
            effort = 'medium'
        budget = self._BUDGET.get(effort, 2048)
        payload['thinking'] = {'type': 'enabled', 'budget_tokens': budget}
        return payload
