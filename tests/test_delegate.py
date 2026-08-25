import io
import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from replio.personas import Persona

from tests.helpers import make_chat


class TestDelegateTool(unittest.TestCase):

    def setUp(self):
        self.chat = make_chat()
        self.sessions_dir = self.chat.config.local_path.parent / 'sessions'

    def tearDown(self):
        self.chat._tmp.cleanup()

    def _delegate_call(self, persona='writer', task='write the doc'):
        return [{
            'id': 'call_del001',
            'type': 'function',
            'function': {'name': 'delegate',
                         'arguments': json.dumps({'persona': persona,
                                                  'task': task})},
        }]

    def _run(self):
        with patch('sys.stdout', new=io.StringIO()):
            self.chat._agent_loop()

    def _tool_msgs(self):
        return [m for m in self.chat.current_session.messages
                if m['role'] == 'tool']

    def _allow_delegate(self, name='writer'):
        self.chat.personas.put(
            Persona(name=name, system_prompt='Writer persona',
                    tool_permission={'delegate': 'allow'}), scope='local')

    def _delegate_logs(self, persona):
        return sorted(self.sessions_dir.glob(f'delegate_{persona}_*.json'))

    def _sub_footer_called(self):
        for c in self.chat._ui.footer.call_args_list:
            args = c[0]
            if len(args) == 2 and not args[1]:
                return True
        return False

    def test_allowed_persona_runs_subagent(self):
        self._allow_delegate()
        self.chat.provider.chat.side_effect = [
            [{'type': 'tool_calls', 'tool_calls': self._delegate_call()}],
            [{'type': 'token', 'content': 'Draft text.'},
             {'type': 'done', 'reason': 'stop'}],
            [{'type': 'token', 'content': 'Final answer.'},
             {'type': 'done', 'reason': 'stop'}],
        ]
        with patch('sys.stdout', new=io.StringIO()):
            self.chat._agent_loop()
        self.assertEqual(self.chat.provider.chat.call_count, 3)
        tools = self._tool_msgs()
        self.assertTrue(tools)
        self.assertIn('[delegate writer] Draft text.', tools[0]['content'])
        self.assertTrue(self._delegate_logs('writer'))

    def test_echo_on_prints_result_and_footer(self):
        self._allow_delegate()
        self.chat._ui.tool_result = MagicMock()
        self.chat._ui.footer = MagicMock()
        self.chat.provider.chat.side_effect = [
            [{'type': 'tool_calls', 'tool_calls': self._delegate_call()}],
            [{'type': 'token', 'content': 'Draft text.'},
             {'type': 'done', 'reason': 'stop'}],
            [{'type': 'token', 'content': 'Final.'},
             {'type': 'done', 'reason': 'stop'}],
        ]
        self._run()
        self.chat._ui.tool_result.assert_called()
        self.assertTrue(self._sub_footer_called())

    def test_echo_off_hides_result_and_footer(self):
        self._allow_delegate()
        self.chat.config.apply('delegate_echo', False)
        self.chat._ui.tool_result = MagicMock()
        self.chat._ui.footer = MagicMock()
        self.chat.provider.chat.side_effect = [
            [{'type': 'tool_calls', 'tool_calls': self._delegate_call()}],
            [{'type': 'token', 'content': 'Draft text.'},
             {'type': 'done', 'reason': 'stop'}],
            [{'type': 'token', 'content': 'Final.'},
             {'type': 'done', 'reason': 'stop'}],
        ]
        self._run()
        self.chat._ui.tool_result.assert_not_called()
        self.assertFalse(self._sub_footer_called())

    def test_default_ask_confirm_applies(self):
        self.chat._ui.confirm = MagicMock(return_value=False)
        self.chat.provider.chat.side_effect = [
            [{'type': 'tool_calls', 'tool_calls': self._delegate_call()}],
            [{'type': 'token', 'content': 'Final.'},
             {'type': 'done', 'reason': 'stop'}],
        ]
        self._run()
        self.assertEqual(self.chat.provider.chat.call_count, 2)
        tools = self._tool_msgs()
        self.assertTrue(tools)
        self.assertIn('[cancelled]', tools[0]['content'])
        self.assertFalse(self._delegate_logs('writer'))

    def test_confirm_granted_runs(self):
        self.chat._ui.confirm = MagicMock(return_value=True)
        self.chat.provider.chat.side_effect = [
            [{'type': 'tool_calls', 'tool_calls': self._delegate_call()}],
            [{'type': 'token', 'content': 'Draft text.'},
             {'type': 'done', 'reason': 'stop'}],
            [{'type': 'token', 'content': 'Final.'},
             {'type': 'done', 'reason': 'stop'}],
        ]
        self._run()
        self.assertEqual(self.chat.provider.chat.call_count, 3)
        self.assertIn('[delegate writer] Draft text.',
                      self._tool_msgs()[0]['content'])

    def test_unknown_persona_denied(self):
        self.chat.provider.chat.side_effect = [
            [{'type': 'tool_calls', 'tool_calls': self._delegate_call('ghost')}],
            [{'type': 'token', 'content': 'Final.'},
             {'type': 'done', 'reason': 'stop'}],
        ]
        self._run()
        self.assertEqual(self.chat.provider.chat.call_count, 2)
        tools = self._tool_msgs()
        self.assertTrue(tools)
        self.assertIn('disabled by tool policy', tools[0]['content'])
        self.assertFalse(self._delegate_logs('ghost'))

    def test_tool_command_delegates(self):
        self._allow_delegate()
        self.chat.provider.chat.side_effect = [
            [{'type': 'token', 'content': 'Sub result.'},
             {'type': 'done', 'reason': 'stop'}],
        ]
        with patch('sys.stdout', new=io.StringIO()) as buf:
            self.chat.registry.dispatch(
                '/tool delegate {"persona": "writer", "task": "write"}')
        self.assertIn('[delegate writer] Sub result.', buf.getvalue())
        self.assertTrue(self._delegate_logs('writer'))

    def test_resolver_actions(self):
        self._allow_delegate()
        self.chat._init_tooling()
        policy = self.chat._tool_policy
        args_allow = {'persona': 'writer', 'task': 't'}
        args_unknown = {'persona': 'ghost', 'task': 't'}
        self.assertEqual(
            policy.action('delegate', 'delegate', None, args_allow), 'allow')
        self.assertEqual(
            policy.action('delegate', 'delegate', None, args_unknown), 'deny')
        self.assertTrue(policy.allowed('delegate', 'delegate'))


if __name__ == '__main__':
    unittest.main()