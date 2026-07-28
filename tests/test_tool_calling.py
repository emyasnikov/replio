import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
import tempfile
import json

from replio.config import Config
from replio.chat import ChatLoop
from replio.sessions.manager import SessionManager


class TestToolCalling(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        config_data = {
            'tool_calling': True,
            'provider': 'ollama',
            'model': 'test-model',
            'base_url': 'https://test.api.com',
            'api_key': '',
            'temperature': 0.7,
            'max_tokens': 2048,
        }

        config_dir = Path(self.temp_dir.name) / '.replio'
        config_dir.mkdir(parents=True, exist_ok=True)
        with open(config_dir / 'config.json', 'w') as f:
            json.dump(config_data, f)

        config = Config(path=self.temp_dir.name)

        self.chat = ChatLoop.__new__(ChatLoop)
        self.chat.config = config
        self.chat.provider = MagicMock()
        sessions_dir = config.local_path.parent / 'sessions'
        self.chat.sessions = SessionManager(sessions_dir)
        self.chat.current_session = self.chat.sessions.create()
        self.chat._tool_registry = None

        self.chat._output_content = MagicMock()
        self.chat._stream_response = MagicMock(return_value='Mocked stream response')
        self.chat._perform_search = MagicMock(return_value='Mocked search context.')
        self.chat._show_tool_status = MagicMock()
        self.chat.session_auto_save = MagicMock()

    def _make_tool_call(self, name='web_search', args='{"query": "test"}'):
        return [{
            'id': 'call_test123',
            'type': 'function',
            'function': {
                'name': name,
                'arguments': args,
            },
        }]

    def test_no_tools_needed(self):
        self.chat.provider.chat_nonstreaming.return_value = {
            'content': 'Hello world',
            'tool_calls': None,
            'finish_reason': 'stop',
            'role': 'assistant',
        }
        self.chat._chat_with_tools()
        self.chat._stream_response.assert_called_once()

    def test_single_tool_then_final(self):
        self.chat.provider.chat_nonstreaming.side_effect = [
            {
                'content': None,
                'tool_calls': self._make_tool_call(),
                'finish_reason': 'tool_calls',
                'role': 'assistant',
            },
            {
                'content': 'Final answer.',
                'tool_calls': None,
                'finish_reason': 'stop',
                'role': 'assistant',
            },
        ]

        with patch('replio.web.search.search', return_value=[
            {'title': 'T', 'url': 'http://x.com', 'snippet': 'S'}
        ]):
            self.chat._chat_with_tools()

        self.chat._show_tool_status.assert_called_once()
        self.chat._stream_response.assert_called_once()
        tool_msgs = [m for m in self.chat.current_session.messages if m['role'] == 'tool']
        self.assertEqual(len(tool_msgs), 1)

    def test_unknown_tool_returns_error(self):
        self.chat.provider.chat_nonstreaming.side_effect = [
            {
                'content': None,
                'tool_calls': self._make_tool_call(name='nonexistent'),
                'finish_reason': 'tool_calls',
                'role': 'assistant',
            },
            {
                'content': 'Recovered.',
                'tool_calls': None,
                'finish_reason': 'stop',
                'role': 'assistant',
            },
        ]

        self.chat._chat_with_tools()

        tool_msgs = [m for m in self.chat.current_session.messages if m['role'] == 'tool']
        self.assertEqual(len(tool_msgs), 1)
        self.assertIn('unknown tool', tool_msgs[0]['content'].lower())
        self.chat._stream_response.assert_called_once()

    def test_force_search_injects_context(self):
        self.chat.provider.chat_nonstreaming.return_value = {
            'content': 'Answer based on search.',
            'tool_calls': None,
            'finish_reason': 'stop',
            'role': 'assistant',
        }
        self.chat._chat_with_tools(force_search='python news')
        self.chat._perform_search.assert_called_once_with('python news', silent=False)
        tool_msgs = [m for m in self.chat.current_session.messages if m['role'] == 'tool']
        self.assertEqual(len(tool_msgs), 1)
        self.assertEqual(tool_msgs[0]['tool_call_id'], 'forced')
        self.chat._stream_response.assert_called_once()

    def test_empty_content_still_streams(self):
        self.chat.provider.chat_nonstreaming.return_value = {
            'content': None,
            'tool_calls': None,
            'finish_reason': 'stop',
            'role': 'assistant',
        }
        self.chat._chat_with_tools()
        self.chat._stream_response.assert_called_once()

    def test_multiple_tool_calls(self):
        self.chat.provider.chat_nonstreaming.side_effect = [
            {
                'content': None,
                'tool_calls': [
                    {'id': 'call_001', 'type': 'function', 'function': {'name': 'web_search', 'arguments': '{"query": "python"}'}},
                    {'id': 'call_002', 'type': 'function', 'function': {'name': 'web_search', 'arguments': '{"query": "rust"}'}},
                ],
                'finish_reason': 'tool_calls',
                'role': 'assistant',
            },
            {
                'content': 'Combined answer.',
                'tool_calls': None,
                'finish_reason': 'stop',
                'role': 'assistant',
            },
        ]

        with patch('replio.web.search.search', return_value=[
            {'title': 'T', 'url': 'http://x.com', 'snippet': 'S'}
        ]):
            self.chat._chat_with_tools()

        self.assertEqual(self.chat._show_tool_status.call_count, 2)
        self.chat._stream_response.assert_called_once()
        tool_msgs = [m for m in self.chat.current_session.messages if m['role'] == 'tool']
        self.assertEqual(len(tool_msgs), 2)

    def test_api_error_returns_gracefully(self):
        self.chat.provider.chat_nonstreaming.return_value = {
            'error': {'code': 401, 'message': 'Unauthorized'},
        }
        self.chat._chat_with_tools()
        self.chat._stream_response.assert_not_called()

    def tearDown(self):
        self.temp_dir.cleanup()


if __name__ == '__main__':
    unittest.main()
