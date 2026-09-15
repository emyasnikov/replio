import io
import unittest
from pathlib import Path
from unittest.mock import patch

from replio.sessions import turns
from replio.sessions.manager import Session
from replio.sessions.render import render_session, turn_summary
from tests.helpers import make_chat


class TestRenderSession(unittest.TestCase):

    def _session(self):
        return Session('test_session')

    def _exchange(self, s, user='Hello there', answer='Hi!', model='llama3.2',
                  provider='ollama', duration=None):
        s.add_user(user, model=model, provider=provider)
        s.add_text(answer)
        turn = s.turns[-1]
        if duration is not None:
            turn['started_at'] = '2026-01-01T00:00:00+00:00'
            turn['ended_at'] = f'2026-01-01T00:00:0{duration}+00:00'
        else:
            s.end_turn('ok')
        return turn

    def test_renders_header_and_user_assistant(self):
        s = self._session()
        self._exchange(s, 'Hello there', 'Hi!', duration=1.5)
        md = render_session(s)
        self.assertIn('# Session: test_session', md)
        self.assertIn('- Turns: 1', md)
        self.assertIn('### User - ', md)
        self.assertIn('Hello there', md)
        self.assertIn('### Assistant - ', md)
        self.assertIn('*ollama:llama3.2 · 1.5s*', md)
        self.assertIn('Hi!', md)

    def test_renders_thinking(self):
        s = self._session()
        s.add_user('q')
        s.add_thinking('First line\nSecond line')
        s.add_text('answer')
        s.end_turn('ok')
        md = render_session(s)
        self.assertIn('### Thinking - ', md)
        self.assertIn('> First line', md)
        self.assertIn('> Second line', md)

    def test_renders_tool_call_and_result(self):
        s = self._session()
        s.add_user('search for x')
        part = s.add_tool('web_search', {'query': 'x'})
        turns.finish_tool(part, 'Results here')
        s.end_turn('ok')
        md = render_session(s)
        self.assertIn('**Tool call: web_search**', md)
        self.assertIn('{"query": "x"}', md)
        self.assertIn('### Tool: web_search - ', md)
        self.assertIn('```text\nResults here\n```', md)

    def test_renders_tool_analysis(self):
        s = self._session()
        s.add_user('q')
        part = s.add_tool('web_search', {})
        turns.finish_tool(part, 'results', analysis='Found the answer')
        s.end_turn('ok')
        md = render_session(s)
        self.assertIn('> _Analysis: Found the answer_', md)

    def test_renders_command_and_compaction(self):
        s = self._session()
        s.add_user('q')
        s.end_turn('ok')
        s.add_command('/compact', summary='THE SUMMARY', compact_from=2)
        md = render_session(s)
        self.assertIn('### Command - ', md)
        self.assertIn('`/compact`', md)
        self.assertIn('Earlier conversation (summarized):', md)
        self.assertIn('> THE SUMMARY', md)
        self.assertIn('trimmed at turn 2', md)

    def test_renders_system_note(self):
        s = self._session()
        s.add_system('web_search context')
        s.end_turn('ok')
        s.add_user('q')
        s.end_turn('ok')
        md = render_session(s)
        self.assertIn('### System - ', md)
        self.assertIn('> web_search context', md)

    def test_renders_errors_section(self):
        s = self._session()
        s.add_user('q')
        s.end_turn('ok')
        s.add_error(401, 'Unauthorized')
        s.add_error(0, 'network down')
        md = render_session(s)
        self.assertIn('## Errors', md)
        self.assertIn('- `401` Unauthorized at ', md)
        self.assertIn('- `0` network down at ', md)

    def test_renders_empty_session_header(self):
        md = render_session(self._session())
        self.assertIn('# Session: test_session', md)
        self.assertIn('- Turns: 0', md)

    def test_fence_grows_past_backticks_in_content(self):
        s = self._session()
        s.add_user('q')
        part = s.add_tool('web_search', {})
        turns.finish_tool(part, 'has ``` code\nand ````` five')
        s.end_turn('ok')
        md = render_session(s)
        self.assertIn('``````text\nhas ``` code\nand ````` five\n``````', md)

    def test_renders_persisted_noise_transform(self):
        s = self._session()
        s.add_user('q')
        part = s.add_tool('fetch_page', {'url': 'x'})
        turns.finish_tool(part, 'page body')
        s.end_turn('ok')
        data = s.to_dict(noise_tools=['fetch_page'])
        restored = Session.from_dict(data)
        md = render_session(restored)
        self.assertIn('excluded from log', md)


class TestTurnSummary(unittest.TestCase):

    def _turn(self, user='hello', status='ok', duration=3.4, tools=None,
              thinking=None):
        s = Session('s')
        s.add_user(user)
        if thinking:
            s.add_thinking(thinking)
        for name, args in (tools or []):
            part = s.add_tool(name, args)
            turns.finish_tool(part, 'out')
        s.add_text('answer')
        s.end_turn(status)
        turn = s.turns[-1]
        if duration is not None:
            turn['started_at'] = '2026-01-01T00:00:00+00:00'
            turn['ended_at'] = f'2026-01-01T00:00:0{duration}+00:00'
        else:
            turn['started_at'] = ''
            turn['ended_at'] = ''
        return turn

    def test_line_format(self):
        line = turn_summary(self._turn())
        self.assertEqual(line, '#1  [ok]  3.4s  0 tools  hello')

    def test_tool_count(self):
        turn = self._turn(tools=[('a', {}), ('b', {})])
        self.assertIn('2 tools', turn_summary(turn))

    def test_singular_tool(self):
        turn = self._turn(tools=[('a', {})])
        self.assertIn('1 tool ', turn_summary(turn))

    def test_running_turn_duration_dash(self):
        turn = self._turn(status='running', duration=None)
        self.assertIn('[running]  -  ', turn_summary(turn))

    def test_command_turn(self):
        s = Session('s')
        s.add_command('/model x')
        turn = s.turns[-1]
        self.assertIn('/model x', turn_summary(turn))

    def test_prompt_first_line(self):
        turn = self._turn(user='one\ntwo')
        self.assertIn('one', turn_summary(turn))
        self.assertNotIn('two', turn_summary(turn))

    def test_thoughts_excerpt(self):
        turn = self._turn(thinking='short thought\nlonger detail')
        summary = turn_summary(turn, thoughts=True)
        self.assertIn('short thought', summary)
        self.assertNotIn('longer detail', summary)
        self.assertIn('\033[90m', summary)

    def test_thoughts_all(self):
        turn = self._turn(thinking='short thought\nlonger detail')
        summary = turn_summary(turn, thoughts='all')
        self.assertIn('short thought', summary)
        self.assertIn('longer detail', summary)

    def test_thoughts_absent_by_default(self):
        turn = self._turn(thinking='hidden')
        self.assertNotIn('hidden', turn_summary(turn))


class TestExportCommand(unittest.TestCase):

    def setUp(self):
        self.chat = make_chat()

    def tearDown(self):
        self.chat._tmp.cleanup()

    def _make_session(self, name='alpha'):
        s = self.chat.sessions.create(name)
        s.add_user('hello')
        s.add_text('hi there')
        s.end_turn('ok')
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
        output = self._dispatch('/sessions export alpha')
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
        self._dispatch(f'/sessions export alpha {target}')
        self.assertTrue(target.exists())
        self.assertIn('# Session: alpha', target.read_text())

    def test_export_stdout(self):
        self._make_session('alpha')
        output = self._dispatch('/sessions export alpha -')
        self.assertIn('# Session: alpha', output)
        self.assertIn('hello', output)

    def test_export_not_found(self):
        output = self._dispatch('/sessions export nosuch')
        self.assertIn('Session not found: nosuch', output)

    def test_export_usage_without_name(self):
        output = self._dispatch('/sessions export')
        self.assertIn('Usage: /sessions export <name> [out]', output)

    def test_export_read_does_not_switch_current(self):
        self._make_session('alpha')
        self.chat.sessions.create('current')
        before = self.chat.sessions.current
        self._dispatch('/sessions export alpha')
        self.assertIs(self.chat.sessions.current, before)
        self.assertEqual(self.chat.sessions.current.name, 'current')

    def test_export_carries_full_log(self):
        s = self._make_session('alpha')
        part = s.add_tool('web_search', {'query': 'x'})
        turns.finish_tool(part, 'results')
        s.end_turn('ok')
        s.add_error(0, 'boom')
        self.chat.sessions.save(s)
        path = self._export_dir() / 'alpha.md'
        self._dispatch('/sessions export alpha')
        body = path.read_text()
        self.assertIn('**Tool call: web_search**', body)
        self.assertIn('### Tool: web_search - ', body)
        self.assertIn('## Errors', body)


if __name__ == '__main__':
    unittest.main()
