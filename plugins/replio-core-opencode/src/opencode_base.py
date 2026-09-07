import uuid

from replio import get_version
from replio.providers.base import OpenAICompatibleProvider


class OpenCodeProviderBase(OpenAICompatibleProvider):
    def __init__(self, **kwargs):
        self.session_id = kwargs.pop('session_id', None) or uuid.uuid4().hex
        super().__init__(**kwargs)

    def _headers(self):
        headers = super()._headers()
        headers['x-opencode-session'] = self.session_id
        headers['User-Agent'] = f'replio/{get_version()}'
        return headers