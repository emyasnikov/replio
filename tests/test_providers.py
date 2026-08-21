import unittest
import tempfile
import json
import threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from replio.config import Config
from replio.chat import ChatLoop
from replio.providers import (
    PROVIDERS, detect_provider,
    OpenAICompatibleProvider, OllamaProvider, OpenAIProvider,
    GroqProvider, AnthropicProvider,
)


class TestProviderDefaults(unittest.TestCase):

    def test_ollama_defaults(self):
        p = OllamaProvider()
        self.assertEqual(p.base_url, 'https://api.ollama.com')
        self.assertEqual(p.model, 'llama3.2')

    def test_openai_defaults(self):
        p = OpenAIProvider()
        self.assertEqual(p.base_url, 'https://api.openai.com/v1')
        self.assertEqual(p.model, 'gpt-4o-mini')

    def test_groq_defaults(self):
        p = GroqProvider()
        self.assertEqual(p.base_url, 'https://api.groq.com/openai/v1')
        self.assertEqual(p.model, 'llama-3.3-70b-versatile')

    def test_anthropic_defaults(self):
        p = AnthropicProvider()
        self.assertEqual(p.base_url, 'https://api.anthropic.com/v1')
        self.assertEqual(p.model, 'claude-sonnet-4-20250514')

    def test_explicit_values_override_defaults(self):
        p = OpenAIProvider(base_url='https://custom.example.com', model='my-model')
        self.assertEqual(p.base_url, 'https://custom.example.com')
        self.assertEqual(p.model, 'my-model')

    def test_openai_compatible_has_no_default_base_url(self):
        p = OpenAICompatibleProvider()
        self.assertEqual(p.base_url, '')


class TestProviderHeaders(unittest.TestCase):

    def test_no_auth_header_without_key(self):
        p = OpenAIProvider(api_key='')
        headers = p._headers()
        self.assertEqual(headers['Content-Type'], 'application/json')
        self.assertNotIn('Authorization', headers)

    def test_bearer_auth_with_key(self):
        p = OpenAIProvider(api_key='sk-test')
        self.assertEqual(p._headers()['Authorization'], 'Bearer sk-test')


class TestDetectProvider(unittest.TestCase):

    def test_detects_known_hosts(self):
        cases = {
            'https://api.openai.com/v1': 'openai',
            'https://api.groq.com/openai/v1': 'groq',
            'https://api.anthropic.com/v1': 'anthropic',
            'https://api.ollama.com': 'ollama',
            'http://localhost:11434': 'openai-compatible',
        }
        for url, expected in cases.items():
            self.assertEqual(detect_provider(url), expected, url)

    def test_detects_empty(self):
        self.assertEqual(detect_provider(''), 'openai-compatible')


class TestProviderRegistry(unittest.TestCase):

    def test_all_names_registered(self):
        for name in ('ollama', 'openai', 'groq', 'anthropic', 'openai-compatible'):
            self.assertIn(name, PROVIDERS)

    def test_all_classes_are_compatible_subclasses(self):
        for factory in PROVIDERS.values():
            self.assertTrue(issubclass(factory, OpenAICompatibleProvider))

    def test_detected_provider_is_registered(self):
        for url in ('https://api.openai.com/v1', 'https://api.groq.com/openai/v1',
                    'https://api.anthropic.com/v1', 'https://api.ollama.com'):
            self.assertIn(detect_provider(url), PROVIDERS)


class TestProviderSwitching(unittest.TestCase):

    def _make_chat(self, data):
        tmp = tempfile.TemporaryDirectory()
        config_dir = Path(tmp.name) / '.replio'
        config_dir.mkdir(parents=True)
        with open(config_dir / 'config.json', 'w') as f:
            json.dump(data, f)
        chat = ChatLoop.__new__(ChatLoop)
        chat.config = Config(path=tmp.name)
        chat.provider = None
        chat._tmp = tmp
        return chat

    def test_switch_resets_default_base_url_and_model(self):
        chat = self._make_chat({
            'provider': 'ollama',
            'base_url': 'https://api.ollama.com',
            'model': 'llama3.2',
        })
        chat._reinit_provider()
        self.assertEqual(type(chat.provider), OllamaProvider)
        chat.config.set('provider', 'openai')
        chat._reinit_provider()
        self.assertEqual(type(chat.provider), OpenAIProvider)
        self.assertEqual(chat.provider.base_url, 'https://api.openai.com/v1')
        self.assertEqual(chat.provider.model, 'gpt-4o-mini')
        self.assertEqual(chat.config.get('base_url'), 'https://api.openai.com/v1')
        chat._tmp.cleanup()

    def test_switch_keeps_custom_base_url_and_model(self):
        chat = self._make_chat({
            'provider': 'ollama',
            'base_url': 'https://proxy.example.com',
            'model': 'llama3.3',
        })
        chat._reinit_provider()
        chat.config.set('provider', 'anthropic')
        chat._reinit_provider()
        self.assertEqual(type(chat.provider), AnthropicProvider)
        self.assertEqual(chat.provider.base_url, 'https://proxy.example.com')
        self.assertEqual(chat.provider.model, 'llama3.3')
        chat._tmp.cleanup()

    def test_unknown_provider_auto_detected(self):
        chat = self._make_chat({
            'provider': 'nope',
            'base_url': 'https://api.groq.com/openai/v1',
            'model': 'test',
        })
        chat._reinit_provider()
        self.assertEqual(type(chat.provider), GroqProvider)
        self.assertEqual(chat.config.get('provider'), 'groq')
        chat._tmp.cleanup()


class _RedirectAPIHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def do_POST(self):
        if self.path == '/start':
            self.send_response(301)
            self.send_header('Location', '/v1/chat/completions')
            self.send_header('Content-Length', '0')
            self.end_headers()
            return
        if self.path == '/v1/chat/completions':
            self.rfile.read(int(self.headers.get('Content-Length', 0)))
            body = json.dumps({
                'choices': [{
                    'message': {'role': 'assistant', 'content': 'ok'},
                    'finish_reason': 'stop',
                }],
            }).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error(404)

    def do_GET(self):
        if self.path == '/v1/chat/completions':
            self.send_error(405, 'Method Not Allowed')
            return
        self.send_error(404)

    def log_message(self, *args):
        pass


class TestPostRedirect(unittest.TestCase):

    def test_nonstreaming_post_survives_301(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), _RedirectAPIHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f'http://127.0.0.1:{server.server_port}'
            p = OpenAIProvider(base_url=base, model='test-model')
            result = p.chat_nonstreaming([{'role': 'user', 'content': 'hi'}])
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
        self.assertEqual(result['role'], 'assistant')
        self.assertEqual(result['content'], 'ok')


class TestProviderEndpoints(unittest.TestCase):

    def test_default_endpoints_no_double_v1(self):
        cases = {
            OllamaProvider: 'https://api.ollama.com/v1/chat/completions',
            OpenAIProvider: 'https://api.openai.com/v1/chat/completions',
            GroqProvider: 'https://api.groq.com/openai/v1/chat/completions',
            AnthropicProvider: 'https://api.anthropic.com/v1/chat/completions',
        }
        for factory, expected in cases.items():
            self.assertEqual(factory()._endpoint(), expected, factory.__name__)

    def test_custom_base_without_v1_appends_v1(self):
        p = OpenAICompatibleProvider(base_url='https://x.example')
        self.assertEqual(p._endpoint(), 'https://x.example/v1/chat/completions')

    def test_custom_base_with_v1_not_doubled(self):
        p = OpenAICompatibleProvider(base_url='https://x.example/v1')
        self.assertEqual(p._endpoint(), 'https://x.example/v1/chat/completions')

    def test_list_models_url_normalized(self):
        import urllib.request
        p = OpenAIProvider()
        captured = {}
        real_urlopen = urllib.request.urlopen

        def _fake_urlopen(req, *args, **kwargs):
            captured['url'] = req.full_url
            raise Exception('stop')

        with unittest.mock.patch('urllib.request.urlopen', _fake_urlopen):
            p.list_models()
        self.assertEqual(captured.get('url'),
                         'https://api.openai.com/v1/models')


class TestReasoningPayload(unittest.TestCase):

    def _payload(self, provider, reasoning):
        p = provider(reasoning=reasoning)
        return p._payload([{'role': 'user', 'content': 'hi'}])

    def test_base_off_sends_nothing(self):
        payload = self._payload(OpenAICompatibleProvider, 'off')
        self.assertNotIn('reasoning_effort', payload)

    def test_base_auto_sends_nothing(self):
        payload = self._payload(OpenAICompatibleProvider, 'auto')
        self.assertNotIn('reasoning_effort', payload)

    def test_base_passes_effort_through(self):
        payload = self._payload(OpenAICompatibleProvider, 'high')
        self.assertEqual(payload['reasoning_effort'], 'high')

    def test_openai_effort(self):
        self.assertEqual(self._payload(OpenAIProvider, 'low')['reasoning_effort'], 'low')
        self.assertEqual(self._payload(OpenAIProvider, 'medium')['reasoning_effort'], 'medium')
        self.assertEqual(self._payload(OpenAIProvider, 'high')['reasoning_effort'], 'high')

    def test_openai_auto_maps_to_medium(self):
        self.assertEqual(self._payload(OpenAIProvider, 'auto')['reasoning_effort'], 'medium')

    def test_openai_off_sends_nothing(self):
        self.assertNotIn('reasoning_effort', self._payload(OpenAIProvider, 'off'))

    def test_anthropic_off_disables_thinking(self):
        payload = self._payload(AnthropicProvider, 'off')
        self.assertEqual(payload['thinking'], {'type': 'disabled'})

    def test_anthropic_effort_budget(self):
        self.assertEqual(self._payload(AnthropicProvider, 'low')['thinking']['budget_tokens'], 1024)
        self.assertEqual(self._payload(AnthropicProvider, 'medium')['thinking']['budget_tokens'], 2048)
        self.assertEqual(self._payload(AnthropicProvider, 'high')['thinking']['budget_tokens'], 4096)

    def test_anthropic_auto_budget(self):
        self.assertEqual(self._payload(AnthropicProvider, 'auto')['thinking']['budget_tokens'], 2048)

    def test_ollama_enable_thinking_on(self):
        self.assertTrue(self._payload(OllamaProvider, 'auto')['enable_thinking'])

    def test_ollama_off_disables_thinking(self):
        self.assertFalse(self._payload(OllamaProvider, 'off')['enable_thinking'])


if __name__ == '__main__':
    unittest.main()
