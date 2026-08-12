import unittest
import io
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from replio.sessions.manager import Session, SessionManager
from tests.helpers import make_chat


class TestSessionModel(unittest.TestCase):

    def test_to_dict_includes_tool_messages(self):
        s = Session('s1')
        s.add_message('user', 'hi')
        s.add_message('assistant', None, tool_calls=[{'id': 'c1'}])
        s.add_message('tool', 'results here', tool_call_id='c1')
        d = s.to_dict()
        self.assertEqual([m['role'] for m in d['messages']], ['user', 'assistant', 'tool'])

    def test_tool_max_chars_truncates_persisted_only(self):
        s = Session('s1')
        s.add_message('tool', 'x' * 100, tool_call_id='c1')
        d = s.to_dict(tool_max_chars=20)
        tool = d['messages'][0]
        self.assertTrue(tool['content'].startswith('x' * 20))
        self.assertIn('truncated from 100 chars', tool['content'])
        self.assertEqual(s.messages[0]['content'], 'x' * 100)

    def test_created_at_defaults_to_now(self):
        s = Session('s1')
        self.assertTrue(s.created_at)
        self.assertEqual(s.updated_at, s.created_at)

    def test_updated_at_bumped_on_message(self):
        s = Session('s1', created_at='2026-01-01T00:00:00+00:00',
                    updated_at='2026-01-01T00:00:00+00:00')
        s.add_message('user', 'hi')
        self.assertEqual(s.created_at, '2026-01-01T00:00:00+00:00')
        self.assertNotEqual(s.updated_at, '2026-01-01T00:00:00+00:00')

    def test_metadata_in_to_dict(self):
        s = Session('s1')
        d = s.to_dict()
        self.assertIn('created_at', d)
        self.assertIn('updated_at', d)
        self.assertEqual(d['errors'], [])

    def test_errors_round_trip(self):
        s = Session('s1')
        s.add_error(401, 'Unauthorized')
        d = s.to_dict()
        self.assertEqual(len(d['errors']), 1)
        self.assertEqual(d['errors'][0]['code'], 401)
        self.assertEqual(d['errors'][0]['message'], 'Unauthorized')
        s2 = Session.from_dict(d)
        self.assertEqual(s2.errors, d['errors'])

    def test_save_load_round_trip(self):
        tmp = tempfile.TemporaryDirectory()
        try:
            sm = SessionManager(Path(tmp.name))
            s = sm.create('test_session')
            s.add_message('user', 'hi')
            s.add_message('assistant', None, tool_calls=[{'id': 'c1'}])
            s.add_message('tool', 'result', tool_call_id='c1')
            s.add_error(0, 'network')
            sm.save(s)
            loaded = sm.load('test_session')
            self.assertEqual([m['role'] for m in loaded.messages],
                             ['user', 'assistant', 'tool'])
            self.assertEqual(loaded.errors, s.errors)
            self.assertEqual(loaded.created_at, s.created_at)
            self.assertEqual(loaded.updated_at, s.updated_at)
        finally:
            tmp.cleanup()

    def test_legacy_file_without_new_keys(self):
        tmp = tempfile.TemporaryDirectory()
        try:
            sm = SessionManager(Path(tmp.name))
            with open(sm.sessions_dir / 'legacy.json', 'w') as f:
                json.dump({'name': 'legacy', 'messages': [{'role': 'user', 'content': 'hi'}]}, f)
            loaded = sm.load('legacy')
            self.assertEqual(loaded.errors, [])
            self.assertTrue(loaded.created_at)
            self.assertTrue(loaded.updated_at)
        finally:
            tmp.cleanup()

    def test_save_applies_tool_max_chars_to_file(self):
        tmp = tempfile.TemporaryDirectory()
        try:
            sm = SessionManager(Path(tmp.name))
            s = sm.create('cap')
            s.add_message('tool', 'x' * 50, tool_call_id='c1')
            sm.save(s, tool_max_chars=10)
            with open(sm.sessions_dir / 'cap.json') as f:
                data = json.load(f)
            self.assertIn('truncated from 50 chars', data['messages'][0]['content'])
            self.assertEqual(s.messages[0]['content'], 'x' * 50)
        finally:
            tmp.cleanup()


class TestSessionLogLoop(unittest.TestCase):

    def setUp(self):
        self.chat = make_chat()

    def tearDown(self):
        self.chat._tmp.cleanup()

    def _make_tool_call(self, name='web_search', args='{"query": "test"}'):
        return [{
            'id': 'call_test123',
            'type': 'function',
            'function': {'name': name, 'arguments': args},
        }]

    def _run(self):
        with patch('sys.stdout', new=io.StringIO()):
            self.chat._agent_loop()

    def _tool_msgs(self):
        return [m for m in self.chat.current_session.messages if m['role'] == 'tool']

    def test_thinking_before_tool_call_persisted(self):
        self.chat.provider.chat.side_effect = [
            [
                {'type': 'thinking', 'content': 'I need to search.'},
                {'type': 'tool_calls', 'tool_calls': self._make_tool_call()},
            ],
            [
                {'type': 'token', 'content': 'Final.'},
                {'type': 'done', 'reason': 'stop'},
            ],
        ]
        with patch('replio.web.search.search', return_value=[
            {'title': 'T', 'url': 'http://x.com', 'snippet': 'S'}
        ]):
            self._run()
        calls = [m for m in self.chat.current_session.messages if m.get('tool_calls')]
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]['thinking'], 'I need to search.')
        self.assertEqual(calls[0]['content'], None)

    def test_tool_analysis_off_by_default(self):
        self.chat.provider.chat.side_effect = [
            [{'type': 'tool_calls', 'tool_calls': self._make_tool_call()}],
            [{'type': 'token', 'content': 'Final.'}, {'type': 'done', 'reason': 'stop'}],
        ]
        with patch('replio.web.search.search', return_value=[
            {'title': 'T', 'url': 'http://x.com', 'snippet': 'S'}
        ]):
            self._run()
        self.chat.provider.chat_nonstreaming.assert_not_called()
        self.assertIsNone(self._tool_msgs()[0]['analysis'])

    def test_tool_analysis_generates_insight_when_enabled(self):
        self.chat.config.set('tool_analysis', True)
        self.chat.provider.chat_nonstreaming.return_value = {
            'role': 'assistant',
            'content': 'Found pages about Python.',
            'tool_calls': None,
            'finish_reason': 'stop',
        }
        self.chat.provider.chat.side_effect = [
            [{'type': 'tool_calls', 'tool_calls': self._make_tool_call()}],
            [{'type': 'token', 'content': 'Final.'}, {'type': 'done', 'reason': 'stop'}],
        ]
        with patch('replio.web.search.search', return_value=[
            {'title': 'T', 'url': 'http://x.com', 'snippet': 'S'}
        ]):
            self._run()
        self.chat.provider.chat_nonstreaming.assert_called_once()
        self.assertEqual(self._tool_msgs()[0]['analysis'], 'Found pages about Python.')

    def test_tool_analysis_skipped_for_cancelled(self):
        self.chat.config.set('tool_analysis', True)
        self.chat._run_tool = unittest.mock.MagicMock(
            return_value='[cancelled] User declined the web_search call')
        self.chat.provider.chat.side_effect = [
            [{'type': 'tool_calls', 'tool_calls': self._make_tool_call()}],
            [{'type': 'token', 'content': 'Final.'}, {'type': 'done', 'reason': 'stop'}],
        ]
        self._run()
        self.chat.provider.chat_nonstreaming.assert_not_called()
        self.assertIsNone(self._tool_msgs()[0]['analysis'])


class TestCompactSession(unittest.TestCase):

    def setUp(self):
        self.chat = make_chat()

    def tearDown(self):
        self.chat._tmp.cleanup()

    def test_compact_replaces_history_with_summary(self):
        for i in range(6):
            self.chat.current_session.add_message('user', f'msg {i}')
            self.chat.current_session.add_message('assistant', f'answer {i}')
        self.chat.provider.chat_nonstreaming.return_value = {
            'role': 'assistant', 'content': 'COMPACTED SUMMARY',
            'tool_calls': None, 'finish_reason': 'stop',
        }
        with patch('sys.stdout', new=io.StringIO()):
            self.chat.compact_session()
        self.chat.provider.chat_nonstreaming.assert_called_once()
        msgs = self.chat.current_session.messages
        self.assertEqual(len(msgs), 5)
        self.assertEqual(msgs[-1]['role'], 'system')
        self.assertIn('COMPACTED SUMMARY', msgs[-1]['content'])
        self.assertEqual([m['content'] for m in msgs[:4]],
                         ['msg 4', 'answer 4', 'msg 5', 'answer 5'])

    def test_compact_nothing_when_no_history(self):
        with patch('sys.stdout', new=io.StringIO()):
            self.chat.compact_session()
        self.chat.provider.chat_nonstreaming.assert_not_called()

    def test_compact_failed_summary_keeps_context(self):
        self.chat.current_session.add_message('user', 'hello')
        self.chat.provider.chat_nonstreaming.return_value = {
            'role': 'assistant', 'content': '', 'tool_calls': None, 'finish_reason': 'stop',
        }
        with patch('sys.stdout', new=io.StringIO()):
            self.chat.compact_session()
        self.assertEqual(len(self.chat.current_session.messages), 1)


if __name__ == '__main__':
    unittest.main()
