import io
import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from replio.types import AgentType

from tests.helpers import make_chat


class TestDelegateTool(unittest.TestCase):

    def setUp(self):
        self.chat = make_chat()
        self.sessions_dir = self.chat.config.local_path.parent / 'sessions'

    def tearDown(self):
        self.chat._tmp.cleanup()

    def _delegate_call(self, type_name='writer', task='write the doc'):
        return [{
            'id': 'call_del001',
            'type': 'function',
            'function': {'name': 'delegate',
                         'arguments': json.dumps({'type': type_name,
                                                  'task': task})},
        }]

    def _run(self):
        with patch('sys.stdout', new=io.StringIO()):
            self.chat._agent_loop()

    def _tool_msgs(self):
        return [m for m in self.chat.current_session.messages
                if m['role'] == 'tool']

    def _allow_delegate(self, name='writer'):
        self.chat.types.put(
            AgentType(name=name, system_prompt='Writer agent',
                      tool_permission={'delegate': 'allow'}), scope='local')

    def _delegate_logs(self, type_name):
        return sorted(
            f for f in self.sessions_dir.glob('sub_*.json')
            if json.loads(f.read_text()).get('parent_id')
            == self.chat.current_session.name)

    def _sub_footer_called(self):
        for c in self.chat._ui.footer.call_args_list:
            args = c[0]
            if len(args) == 2 and not args[1]:
                return True
        return False

    def test_allowed_type_runs_subagent(self):
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

    def test_default_allow_does_not_prompt(self):
        self.chat._ui.confirm = MagicMock()
        self.chat.provider.chat.side_effect = [
            [{'type': 'tool_calls', 'tool_calls': self._delegate_call()}],
            [{'type': 'token', 'content': 'Draft text.'},
             {'type': 'done', 'reason': 'stop'}],
            [{'type': 'token', 'content': 'Final.'},
             {'type': 'done', 'reason': 'stop'}],
        ]
        self._run()
        self.assertEqual(self.chat.provider.chat.call_count, 3)
        self.chat._ui.confirm.assert_not_called()
        self.assertIn('[delegate writer] Draft text.',
                      self._tool_msgs()[0]['content'])

    def test_type_ask_requires_confirm(self):
        self.chat.types.put(
            AgentType(name='writer', system_prompt='W',
                      tool_permission={'delegate': 'ask'}), scope='local')
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
        self.chat.types.put(
            AgentType(name='writer', system_prompt='W',
                      tool_permission={'delegate': 'ask'}), scope='local')
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

    def test_unknown_type_denied(self):
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

    def test_tool_command_delegates_single_print(self):
        self._allow_delegate()
        self.chat.provider.chat.side_effect = [
            [{'type': 'token', 'content': 'Sub result.'},
             {'type': 'done', 'reason': 'stop'}],
        ]
        with patch('sys.stdout', new=io.StringIO()) as buf:
            self.chat.registry.dispatch(
                '/tool delegate {"type": "writer", "task": "write"}')
        out = buf.getvalue()
        self.assertEqual(out.count('[delegate writer] Sub result.'), 1)
        self.assertTrue(self._delegate_logs('writer'))

    def test_resolver_actions(self):
        self._allow_delegate()
        self.chat._init_tooling()
        policy = self.chat._tool_policy
        args_allow = {'type': 'writer', 'task': 't'}
        args_default = {'type': 'programmer', 'task': 't'}
        args_unknown = {'type': 'ghost', 'task': 't'}
        self.assertEqual(
            policy.action('delegate', 'delegate', None, args_allow), 'allow')
        self.assertEqual(
            policy.action('delegate', 'delegate', None, args_default), 'allow')
        self.assertEqual(
            policy.action('delegate', 'delegate', None, args_unknown), 'deny')
        self.assertTrue(policy.allowed('delegate', 'delegate'))

    def test_empty_result_uses_log_summary(self):
        from types import SimpleNamespace
        from replio.sessions.manager import Session
        from replio.tools.delegate import _format_result
        subname = 'sub_20260825_000000_ses_20260825_000000_parent'
        sess = Session(subname, messages=[
            {'role': 'user', 'content': 'build the dungeon'},
            {'role': 'assistant', 'tool_calls': [{'id': 'c1'}]},
            {'role': 'tool', 'content': 'Created /tmp/x/main.py (40 lines, 900 chars)',
             'tool': 'file_write', 'tool_call_id': 'c1'},
            {'role': 'assistant', 'tool_calls': [{'id': 'c2'}]},
            {'role': 'tool', 'content': '$ cd /tmp/x && pytest\n1 passed',
             'tool': 'bash', 'tool_call_id': 'c2'},
        ])
        self.chat.sessions.save(sess)
        result = SimpleNamespace(status='ok', content='', session=subname,
                                 errors=[], usage=None)
        out = _format_result(self.chat, 'programmer', result)
        self.assertIn('no final text', out)
        self.assertIn('2 tool calls', out)
        self.assertIn('wrote:', out)
        self.assertIn('main.py', out)
        self.assertIn('last bash', out)


if __name__ == '__main__':
    unittest.main()