import unittest
import io
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
        self._run()
        self.assertEqual(self._assistant_msgs(), [])
        self.chat.session_auto_save.assert_called()


if __name__ == '__main__':
    unittest.main()
