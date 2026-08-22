import io
import unittest
from pathlib import Path
from unittest.mock import patch

from replio.sessions.manager import Session
from replio.sessions.render import render_session
from tests.helpers import make_chat


class TestRenderSession(unittest.TestCase):

    def _session(self):
        return Session('test_session')

    def test_renders_header_and_user_assistant(self):
        s = self._session()
        s.add_message('user', 'Hello there')
        s.add_message('assistant', 'Hi!', model='llama3.2', provider='ollama',
                      duration=1.5)
        md = render_session(s)
        self.assertIn('# Session: test_session', md)
        self.assertIn('- Messages: 2', md)
        self.assertIn('### User - ', md)
        self.assertIn('Hello there', md)
        self.assertIn('### Assistant - ', md)
        self.assertIn('*ollama:llama3.2 · 1.5s*', md)
        self.assertIn('Hi!', md)

    def test_renders_thinking(self):
        s = self._session()
        s.add_message('user', 'q')
        s.add_message('assistant', 'answer', thinking='First line\nSecond line')
        md = render_session(s)
        self.assertIn('> _Thinking:_', md)
        self.assertIn('> First line', md)
        self.assertIn('> Second line', md)

    def test_renders_tool_call_and_result(self):
        s = self._session()
        s.add_message('user', 'search for x')
        s.add_message('assistant', None, tool_calls=[{
            'id': 'c1', 'type': 'function',
            'function': {'name': 'web_search', 'arguments': '{"query": "x"}'},
        }])
        s.add_message('tool', 'Results here', tool_call_id='c1', tool='web_search')
        md = render_session(s)
        self.assertIn('**Tool call: web_search**', md)
        self.assertIn('{"query": "x"}', md)
        self.assertIn('### Tool: web_search - ', md)
        self.assertIn('```text\nResults here\n```', md)

    def test_renders_tool_analysis(self):
        s = self._session()
        s.add_message('user', 'q')
        s.add_message('assistant', None, tool_calls=[{
            'id': 'c1', 'type': 'function',
            'function': {'name': 'web_search', 'arguments': '{}'},
        }])
        s.add_message('tool', 'results', tool_call_id='c1', tool='web_search',
                      analysis='Found the answer')
        md = render_session(s)
        self.assertIn('> _Analysis: Found the answer_', md)

    def test_renders_command_and_compaction(self):
        s = self._session()
        s.add_message('user', 'q')
        s.add_message('command', '/compact', result='THE SUMMARY', compact_from=2)
        md = render_session(s)
        self.assertIn('### Command - ', md)
        self.assertIn('`/compact`', md)
        self.assertIn('Earlier conversation (summarized):', md)
        self.assertIn('> THE SUMMARY', md)
        self.assertIn('trimmed at message index 2', md)

    def test_renders_system_note(self):
        s = self._session()
        s.add_message('system', 'web_search context')
        s.add_message('user', 'q')
        md = render_session(s)
        self.assertIn('### System - ', md)
        self.assertIn('> web_search context', md)

    def test_renders_errors_section(self):
        s = self._session()
        s.add_message('user', 'q')
        s.add_error(401, 'Unauthorized')
        s.add_error(0, 'network down')
        md = render_session(s)
        self.assertIn('## Errors', md)
        self.assertIn('- `401` Unauthorized at ', md)
        self.assertIn('- `0` network down at ', md)

    def test_renders_empty_session_header(self):
        md = render_session(self._session())
        self.assertIn('# Session: test_session', md)
        self.assertIn('- Messages: 0', md)

    def test_fence_grows_past_backticks_in_content(self):
        s = self._session()
        s.add_message('user', 'q')
        s.add_message('tool', 'has ``` code\nand ````` five', tool_call_id='c1',
                      tool='web_search')
        md = render_session(s)
        self.assertIn('``````text\nhas ``` code\nand ````` five\n``````', md)

    def test_renders_persisted_noise_transform(self):
        s = self._session()
        s.add_message('user', 'q')
        s.add_message('assistant', None, tool_calls=[{
            'id': 'c1', 'type': 'function',
            'function': {'name': 'fetch_page', 'arguments': '{"url": "x"}'},
        }])
        s.add_message('tool', 'page body', tool_call_id='c1', tool='fetch_page')
        data = s.to_dict(noise_tools=['fetch_page'])
        restored = Session.from_dict(data)
        md = render_session(restored)
        self.assertIn('excluded from log', md)


class TestExportCommand(unittest.TestCase):

    def setUp(self):
        self.chat = make_chat()

    def tearDown(self):
        self.chat._tmp.cleanup()

    def _make_session(self, name='alpha'):
        s = self.chat.sessions.create(name)
        s.add_message('user', 'hello')
        s.add_message('assistant', 'hi there')
        self.chat.sessions.save(s)
        return s

    def _dispatch(self, line):
        out = io.StringIO()
        with patch('sys.stdout', new=out):
            self.chat.registry.dispatch(line)
        return out.getvalue()

    def _export_dir(self):
        return self.chat.sessions.sessions_dir.parent / 'exports'

    def test_export_writes_default_file(self):
        self._make_session('alpha')
        output = self._dispatch('/session export alpha')
        path = self._export_dir() / 'alpha.md'
        self.assertTrue(path.exists())
        body = path.read_text()
        self.assertIn('# Session: alpha', body)
        self.assertIn('hello', body)
        self.assertIn('hi there', body)
        self.assertIn(f'Exported session: alpha -> {path}', output)

    def test_export_custom_out_path(self):
        self._make_session('alpha')
        tmp = self.chat._tmp.name
        target = Path(tmp) / 'custom' / 'out.md'
        self._dispatch(f'/session export alpha {target}')
        self.assertTrue(target.exists())
        self.assertIn('# Session: alpha', target.read_text())

    def test_export_stdout(self):
        self._make_session('alpha')
        output = self._dispatch('/session export alpha -')
        self.assertIn('# Session: alpha', output)
        self.assertIn('hello', output)

    def test_export_not_found(self):
        output = self._dispatch('/session export nosuch')
        self.assertIn('Session not found: nosuch', output)

    def test_export_usage_without_name(self):
        output = self._dispatch('/session export')
        self.assertIn('Usage: /session export <name> [out]', output)

    def test_export_read_does_not_switch_current(self):
        self._make_session('alpha')
        self.chat.sessions.create('current')
        before = self.chat.sessions.current
        self._dispatch('/session export alpha')
        self.assertIs(self.chat.sessions.current, before)
        self.assertEqual(self.chat.sessions.current.name, 'current')

    def test_export_carries_full_log(self):
        s = self._make_session('alpha')
        s.add_message('user', 'q')
        s.add_message('assistant', None, tool_calls=[{
            'id': 'c1', 'type': 'function',
            'function': {'name': 'web_search', 'arguments': '{"query": "x"}'},
        }])
        s.add_message('tool', 'results', tool_call_id='c1', tool='web_search')
        s.add_error(0, 'boom')
        self.chat.sessions.save(s)
        path = self._export_dir() / 'alpha.md'
        self._dispatch('/session export alpha')
        body = path.read_text()
        self.assertIn('**Tool call: web_search**', body)
        self.assertIn('### Tool: web_search - ', body)
        self.assertIn('## Errors', body)


if __name__ == '__main__':
    unittest.main()