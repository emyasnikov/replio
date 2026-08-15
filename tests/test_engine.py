import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from replio.config import Config
from replio.engine import Engine
from replio.plugins.manager import PluginManager
from replio.sessions.manager import SessionManager
from replio.ui import HeadlessUI


def make_engine(config_data: dict | None = None) -> Engine:
    temp_dir = tempfile.TemporaryDirectory()
    data = {
        'tool_calling': True,
        'provider': 'ollama',
        'model': 'test-model',
        'base_url': 'https://test.api.com',
        'api_key': '',
        'temperature': 0.7,
        'max_tokens': 2048,
    }
    if config_data:
        data.update(config_data)
    config_dir = Path(temp_dir.name) / '.replio'
    config_dir.mkdir(parents=True, exist_ok=True)
    with open(config_dir / 'config.json', 'w') as f:
        json.dump(data, f)

    config = Config(path=temp_dir.name)
    engine = Engine.__new__(Engine)
    engine.config = config
    engine.provider = MagicMock()
    sessions_dir = config.local_path.parent / 'sessions'
    engine.sessions = SessionManager(sessions_dir)
    engine.current_session = engine.sessions.create()
    engine._tool_registry = None
    engine._plugin_manager = PluginManager(config)
    engine._plugin_manager.load()
    engine._tmp = temp_dir
    return engine


class TestEngine(unittest.TestCase):

    def setUp(self):
        self.engine = make_engine()

    def tearDown(self):
        self.engine._tmp.cleanup()

    def test_chat_returns_turn_result(self):
        self.engine.provider.chat.return_value = [
            {'type': 'token', 'content': 'Hello world'},
            {'type': 'done', 'reason': 'stop'},
        ]
        result = self.engine.chat('hi')
        self.assertEqual(result.content, 'Hello world')
        self.assertEqual(result.status, 'ok')
        self.assertEqual(result.provider, 'ollama')
        self.assertEqual(result.session, self.engine.current_session.name)
        roles = [m['role'] for m in self.engine.current_session.messages]
        self.assertEqual(roles, ['user', 'assistant'])
        self.assertEqual(result.tool_calls, [])
        self.assertEqual(result.errors, [])

    def test_thinking_separated_from_content(self):
        self.engine.provider.chat.return_value = [
            {'type': 'token', 'content': '<thinking>hmm</thinking>Answer'},
            {'type': 'done', 'reason': 'stop'},
        ]
        result = self.engine.chat('q')
        self.assertEqual(result.content, 'Answer')
        self.assertEqual(result.thinking, '<thinking>hmm')

    def test_provider_thinking_event_accumulates(self):
        self.engine.provider.chat.return_value = [
            {'type': 'thinking', 'content': 'reasoning'},
            {'type': 'token', 'content': 'Answer'},
            {'type': 'done', 'reason': 'stop'},
        ]
        result = self.engine.chat('q')
        self.assertEqual(result.thinking, 'reasoning')
        self.assertEqual(result.content, 'Answer')

    def test_error_status_and_errors(self):
        self.engine.provider.chat.return_value = [
            {'type': 'error', 'code': 401, 'message': 'Unauthorized'},
        ]
        result = self.engine.chat('q')
        self.assertEqual(result.status, 'error')
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(result.errors[0]['code'], 401)
        self.assertEqual(result.errors[0]['message'], 'Unauthorized')

    def test_load_or_create_session_persists_and_reloads(self):
        self.engine.load_or_create_session('foo')
        self.assertEqual(self.engine.current_session.name, 'foo')
        self.engine.provider.chat.return_value = [
            {'type': 'token', 'content': 'Answer'},
            {'type': 'done', 'reason': 'stop'},
        ]
        self.engine.chat('q', autoname=False)
        self.assertEqual(self.engine.current_session.name, 'foo')
        self.assertTrue((self.engine.sessions.sessions_dir / 'foo.json').exists())
        self.engine.load_or_create_session('foo')
        self.assertEqual(self.engine.current_session.name, 'foo')
        self.assertEqual(len(self.engine.current_session.messages), 2)

    def test_headless_confirm_policy(self):
        self.engine._init_tooling()
        self.engine._ui = HeadlessUI(auto='deny')
        out = self.engine._run_tool('run_command', {'command': 'echo hi'})
        self.assertEqual(out, '[cancelled] User declined the run_command call')
        self.engine._ui = HeadlessUI(auto='allow')
        self.assertEqual(self.engine._confirm_tool('run_command', {'command': 'echo hi'}), True)

    def test_denied_ask_tool_feeds_cancelled_result(self):
        self.engine.provider.chat.side_effect = [
            [{'type': 'tool_calls', 'tool_calls': [{
                'id': 'c1', 'type': 'function',
                'function': {'name': 'run_command', 'arguments': '{"command": "echo hi"}'},
            }]}],
            [{'type': 'token', 'content': 'Final answer'},
             {'type': 'done', 'reason': 'stop'}],
        ]
        result = self.engine.chat('q')
        tool_msgs = [m for m in self.engine.current_session.messages if m['role'] == 'tool']
        self.assertEqual(len(tool_msgs), 1)
        self.assertTrue(tool_msgs[0]['content'].startswith('[cancelled]'))
        self.assertEqual(result.content, 'Final answer')
        self.assertEqual(result.tool_calls, [{'name': 'run_command', 'arguments': {'command': 'echo hi'}}])

    def test_turn_result_to_dict_json_serializable(self):
        self.engine.provider.chat.return_value = [
            {'type': 'token', 'content': 'Hello'},
            {'type': 'done', 'reason': 'stop', 'usage': {'prompt_tokens': 10}},
        ]
        result = self.engine.chat('q')
        d = result.to_dict()
        self.assertEqual(d['content'], 'Hello')
        self.assertEqual(d['usage'], {'prompt_tokens': 10})
        self.assertIn('session', d)
        self.assertIn('status', d)
        json.dumps(d)


class TestEngineSinks(unittest.TestCase):

    def test_null_ui_confirm_denies(self):
        from replio.ui import NullUI
        self.assertEqual(NullUI().confirm('x', 'x'), False)

    def test_headless_ui_auto(self):
        self.assertEqual(HeadlessUI(auto='allow').confirm('x', 'x'), True)
        self.assertEqual(HeadlessUI(auto='deny').confirm('x', 'x'), False)


if __name__ == '__main__':
    unittest.main()
