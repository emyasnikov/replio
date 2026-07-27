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

    def _payload(self, messages, stream=False, tools=None):
        payload = {
            'model': self.model,
            'messages': messages,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens,
            'stream': stream,
        }
        if tools:
            payload['tools'] = tools
        return payload

    def _post(self, payload):
        url = f'{self.base_url}/v1/chat/completions'
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers=self._headers())
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())

    def chat_nonstreaming(self, messages: list[dict],
                          tools: list[dict] | None = None) -> dict:
        payload = self._payload(messages, stream=False, tools=tools)
        result = self._post(payload)
        choice = result['choices'][0]
        message = choice['message']
        return {
            'role': message.get('role', 'assistant'),
            'content': message.get('content'),
            'tool_calls': message.get('tool_calls'),
            'finish_reason': choice.get('finish_reason'),
        }

    def chat(self, messages: list[dict], stream: bool = True):
        payload = self._payload(messages, stream=stream)

        if not stream:
            result = self._post(payload)
            content = result['choices'][0]['message']['content']
            yield {'type': 'token', 'content': content}
            yield {'type': 'done'}
            return

        for event in stream_sse(self._endpoint(), self._headers(), payload):
            if 'type' in event:
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

    def _endpoint(self):
        return f'{self.base_url}/v1/chat/completions'

    def list_models(self) -> list[str]:
        url = f'{self.base_url}/v1/models'
        req = urllib.request.Request(url, headers=self._headers())
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
        return [m['id'] for m in data.get('data', [])]
