import json
import urllib.request
import urllib.error

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
        try:
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', errors='replace')
            return {'error': {'code': e.code, 'message': body}}
        except urllib.error.URLError as e:
            return {'error': {'code': 0, 'message': f'Network error: {e.reason}'}}
        except Exception as e:
            return {'error': {'code': 0, 'message': str(e)}}

    def chat_nonstreaming(self, messages: list[dict],
                          tools: list[dict] | None = None) -> dict:
        payload = self._payload(messages, stream=False, tools=tools)
        result = self._post(payload)
        if 'error' in result:
            return result
        choice = result['choices'][0]
        message = choice['message']
        return {
            'role': message.get('role', 'assistant'),
            'content': message.get('content'),
            'tool_calls': message.get('tool_calls'),
            'finish_reason': choice.get('finish_reason'),
        }

    def chat(self, messages: list[dict], stream: bool = True,
             tools: list[dict] | None = None):
        payload = self._payload(messages, stream=stream, tools=tools)

        if not stream:
            result = self._post(payload)
            if 'error' in result:
                yield {'type': 'error', 'code': result['error']['code'], 'message': result['error']['message']}
                return
            content = result['choices'][0]['message']['content']
            yield {'type': 'token', 'content': content}
            yield {'type': 'done'}
            return

        tool_calls_acc: dict[int, dict] = {}
        for event in stream_sse(self._endpoint(), self._headers(), payload):
            if 'type' in event:
                yield event
                return
            choices = event.get('choices', [])
            if not choices:
                continue
            delta = choices[0].get('delta', {})
            reasoning = delta.get('reasoning_content', '')
            if reasoning:
                yield {'type': 'thinking', 'content': reasoning}
                continue
            for tc in delta.get('tool_calls', []):
                idx = tc.get('index', 0)
                entry = tool_calls_acc.setdefault(idx, {
                    'id': '', 'type': 'function',
                    'function': {'name': '', 'arguments': ''},
                })
                if tc.get('id'):
                    entry['id'] = tc['id']
                fn = tc.get('function', {})
                if fn.get('name'):
                    entry['function']['name'] = fn['name']
                if fn.get('arguments'):
                    entry['function']['arguments'] += fn['arguments']
            content = delta.get('content', '')
            if content:
                yield {'type': 'token', 'content': content}
            finish = choices[0].get('finish_reason')
            if finish:
                if tool_calls_acc:
                    yield {'type': 'tool_calls', 'tool_calls': list(tool_calls_acc.values())}
                else:
                    yield {'type': 'done', 'reason': finish}

    def _endpoint(self):
        return f'{self.base_url}/v1/chat/completions'

    def list_models(self) -> list[str]:
        url = f'{self.base_url}/v1/models'
        req = urllib.request.Request(url, headers=self._headers())
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read())
            return [m['id'] for m in data.get('data', [])]
        except Exception as e:
            print(f'\001\033[91m\002[Error]\001\033[0m\002 Failed to list models: {e}')
            return []
