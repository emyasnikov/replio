import json
import urllib.request

from .base import BaseProvider
from ..utils.http import stream_sse


class OllamaProvider(BaseProvider):
    DEFAULT_BASE_URL = 'https://api.ollama.com'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.base_url:
            self.base_url = self.DEFAULT_BASE_URL

    def _headers(self):
        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        return headers

    def chat(self, messages: list[dict], stream: bool = True):
        url = f'{self.base_url}/v1/chat/completions'
        payload = {
            'model': self.model,
            'messages': messages,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens,
            'stream': stream,
        }

        if not stream:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(url, data=data,
                                         headers=self._headers())
            with urllib.request.urlopen(req) as resp:
                result = json.loads(resp.read())
            content = result['choices'][0]['message']['content']
            yield {'type': 'token', 'content': content}
            yield {'type': 'done'}
            return

        for event in stream_sse(url, self._headers(), payload):
            if event['type'] in ('done', 'error'):
                yield event
                return
            choices = event.get('choices', [])
            if not choices:
                continue
            delta = choices[0].get('delta', {})
            content = delta.get('content', '')
            if content:
                yield {'type': 'token', 'content': content}
            finish = choices[0].get('finish_reason')
            if finish:
                yield {'type': 'done', 'reason': finish}

    def list_models(self) -> list[str]:
        url = f'{self.base_url}/v1/models'
        req = urllib.request.Request(url, headers=self._headers())
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
        return [m['id'] for m in data.get('data', [])]
