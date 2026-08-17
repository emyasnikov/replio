import unittest
import io
import json
from unittest.mock import patch

from tests.helpers import make_chat


class TestAgentLoop(unittest.TestCase):

    def setUp(self):
        self.chat = make_chat()

    def tearDown(self):
        self.chat._tmp.cleanup()

    def _run(self):
        with patch('sys.stdout', new=io.StringIO()):
            self.chat._agent_loop()

    def _assistant_msgs(self):
        return [m for m in self.chat.current_session.messages if m['role'] == 'assistant']

    def test_no_tools_single_round_trip(self):
        self.chat.provider.chat.return_value = [
            {'type': 'token', 'content': 'Hello world'},
            {'type': 'done', 'reason': 'stop'},
        ]
        self._run()
        self.chat.provider.chat.assert_called_once()
        msgs = self._assistant_msgs()
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0]['content'], 'Hello world')
        self.chat.session_auto_save.assert_called()

    def test_thinking_persisted_as_metadata_not_content(self):
        self.chat.provider.chat.return_value = [
            {'type': 'thinking', 'content': 'reasoning...'},
            {'type': 'token', 'content': 'Answer'},
            {'type': 'done', 'reason': 'stop'},
        ]
        self._run()
        msgs = self._assistant_msgs()
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0]['content'], 'Answer')
        self.assertEqual(msgs[0]['thinking'], 'reasoning...')

    def test_error_bails_gracefully_and_is_persisted(self):
        self.chat.provider.chat.return_value = [
            {'type': 'error', 'code': 401, 'message': 'Unauthorized'},
        ]
        self._run()
        self.assertEqual(self._assistant_msgs(), [])
        self.chat.session_auto_save.assert_called()
        errors = self.chat.current_session.errors
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['code'], 401)
        self.assertEqual(errors[0]['message'], 'Unauthorized')

    def test_empty_stream_persists_nothing(self):
        self.chat.provider.chat.return_value = []
        out = io.StringIO()
        with patch('sys.stdout', new=out):
            self.chat._agent_loop()
        self.assertEqual(self._assistant_msgs(), [])
        self.chat.session_auto_save.assert_called()
        errors = self.chat.current_session.errors
        self.assertEqual(len(errors), 1)
        self.assertIn('Stream ended before a completion event', errors[0]['message'])
        self.assertEqual(self.chat.provider.chat.call_count, 3)
        self.assertEqual(out.getvalue().count('retrying'), 2)

    def test_empty_stream_retried_once_then_succeeds(self):
        self.chat.provider.chat.side_effect = [
            [],
            [
                {'type': 'token', 'content': 'Recovered answer'},
                {'type': 'done', 'reason': 'stop'},
            ],
        ]
        self._run()
        self.assertEqual(self.chat.provider.chat.call_count, 2)
        self.assertEqual(self.chat.current_session.errors, [])
        self.assertEqual(self._assistant_msgs()[0]['content'], 'Recovered answer')

    def test_empty_stream_retried_twice_then_succeeds(self):
        self.chat.provider.chat.side_effect = [
            [],
            [],
            [
                {'type': 'token', 'content': 'Recovered answer'},
                {'type': 'done', 'reason': 'stop'},
            ],
        ]
        self._run()
        self.assertEqual(self.chat.provider.chat.call_count, 3)
        self.assertEqual(self.chat.current_session.errors, [])
        self.assertEqual(self._assistant_msgs()[0]['content'], 'Recovered answer')

    def test_failed_follow_up_stream_hints_recovery(self):
        target = self.chat.config.local_path.parent.parent / 'a.txt'
        target.write_text('hello\n')
        self.chat.provider.chat.side_effect = [
            [{'type': 'tool_calls', 'tool_calls': [
                {'id': 'call_1', 'type': 'function',
                 'function': {'name': 'read_file',
                              'arguments': json.dumps({'path': str(target)})}},
            ]}],
            [],
            [],
            [],
        ]
        out = io.StringIO()
        with patch('sys.stdout', new=out):
            self.chat._agent_loop()
        errors = self.chat.current_session.errors
        self.assertEqual(len(errors), 1)
        self.assertIn('Stream ended before a completion event', errors[0]['message'])
        self.assertIn('tool results are saved', out.getvalue())
        self.assertIn('retrying', out.getvalue())
        tool_msgs = [m for m in self.chat.current_session.messages if m['role'] == 'tool']
        self.assertEqual(len(tool_msgs), 1)

    def test_token_stream_then_eof_persists_content_and_logs_error(self):
        self.chat.provider.chat.return_value = [
            {'type': 'token', 'content': 'Partial answer'},
        ]
        self._run()
        self.assertEqual(self._assistant_msgs()[0]['content'], 'Partial answer')
        errors = self.chat.current_session.errors
        self.assertEqual(len(errors), 1)
        self.assertIn('Stream ended before a completion event', errors[0]['message'])

    def test_empty_done_logs_error(self):
        self.chat.provider.chat.return_value = [
            {'type': 'done', 'reason': 'stop'},
        ]
        self._run()
        self.assertEqual(self._assistant_msgs(), [])
        errors = self.chat.current_session.errors
        self.assertEqual(len(errors), 1)
        self.assertIn('empty response', errors[0]['message'])

    def test_mid_stream_exception_is_caught_and_logged(self):
        def _raising():
            yield {'type': 'token', 'content': 'Partial'}
            raise RuntimeError('boom')

        self.chat.provider.chat.return_value = _raising()
        self._run()
        self.assertEqual(self._assistant_msgs()[0]['content'], 'Partial')
        errors = self.chat.current_session.errors
        self.assertEqual(len(errors), 1)
        self.assertIn('Agent loop failed: boom', errors[0]['message'])

    def test_length_finish_logs_truncation_error(self):
        self.chat.provider.chat.return_value = [
            {'type': 'token', 'content': 'Part of an answer'},
            {'type': 'done', 'reason': 'length'},
        ]
        self._run()
        errors = self.chat.current_session.errors
        self.assertEqual(len(errors), 1)
        self.assertIn('max_tokens', errors[0]['message'])
        self.assertEqual(self._assistant_msgs()[0]['content'], 'Part of an answer')

    def test_context_size_printed_after_response(self):
        self.chat.provider.chat.return_value = [
            {'type': 'token', 'content': 'Hello'},
            {'type': 'done', 'reason': 'stop'},
        ]
        out = io.StringIO()
        with patch('sys.stdout', new=out):
            self.chat._agent_loop()
        value = out.getvalue()
        self.assertIn('s, ', value)
        self.assertIn('tokens', value)

    def test_footer_uses_provider_usage(self):
        self.chat.provider.chat.return_value = [
            {'type': 'token', 'content': 'Hello'},
            {'type': 'done', 'reason': 'stop',
             'usage': {'prompt_tokens': 29238, 'completion_tokens': 5,
                       'total_tokens': 29243}},
        ]
        out = io.StringIO()
        with patch('sys.stdout', new=out):
            self.chat._agent_loop()
        self.assertIn('29,238 tokens', out.getvalue())

    def test_clear_screen_on_repl_start_default(self):
        out = io.StringIO()
        with patch('sys.stdout', new=out):
            with patch('replio.chat.input', side_effect=EOFError):
                self.chat.run()
        self.assertIn('\033[3J\033[2J\033[H', out.getvalue())

    def test_clear_screen_disabled_suppresses_escape(self):
        self.chat.config.data['clear_screen'] = False
        out = io.StringIO()
        with patch('sys.stdout', new=out):
            with patch('replio.chat.input', side_effect=EOFError):
                self.chat.run()
        self.assertNotIn('\033[3J\033[2J\033[H', out.getvalue())
        self.assertIn('Replio', out.getvalue())

    def test_banner_shows_version_by_default(self):
        from replio import get_version
        out = io.StringIO()
        with patch('sys.stdout', new=out):
            with patch('replio.chat.input', side_effect=EOFError):
                self.chat.run()
        self.assertIn(f'v{get_version()}', out.getvalue())

    def test_banner_version_omitted_when_disabled(self):
        from replio import get_version
        self.chat.config.data['show_version'] = False
        out = io.StringIO()
        with patch('sys.stdout', new=out):
            with patch('replio.chat.input', side_effect=EOFError):
                self.chat.run()
        self.assertNotIn(f'v{get_version()}', out.getvalue())


if __name__ == '__main__':
    unittest.main()
