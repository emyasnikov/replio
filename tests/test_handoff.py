import io
import json
import unittest
from unittest.mock import patch

from tests.helpers import make_chat


class TestHandoffTool(unittest.TestCase):

    def setUp(self):
        self.chat = make_chat()
        self.chat._bind_assistant()
        self.chat._init_tooling()

    def tearDown(self):
        self.chat._tmp.cleanup()

    def _handoff(self, target, done=False):
        return self.chat._run_tool('handoff', {'target': target, 'done': done})

    def test_registered(self):
        self.assertIn('handoff', self.chat._tool_registry.names())
        self.assertEqual(self.chat._tool_registry.permission_for('handoff'), 'handoff')

    def test_handoff_to_role_sets_pending_and_pauses(self):
        out = self._handoff('writer')
        self.assertTrue(out.startswith('[handoff]'))
        self.assertEqual(self.chat._pending_handoff['role'], 'writer')
        self.assertEqual(self.chat.current_run.status, 'paused')

    def test_done_finishes_the_run(self):
        self._handoff('writer', done=True)
        self.assertEqual(self.chat.current_run.status, 'done')
        self.assertTrue(self.chat.current_run.ended_at)

    def test_unknown_target_errors_without_pausing(self):
        out = self._handoff('ghost')
        self.assertTrue(out.startswith('Error'))
        self.assertEqual(self.chat.current_run.status, 'running')
        self.assertIsNone(self.chat._pending_handoff)

    def test_handoff_to_parent_from_role(self):
        writer = self.chat.focus.focus_role('writer')
        writer._init_tooling()
        out = writer._run_tool('handoff', {'target': 'parent'})
        self.assertTrue(out.startswith('[handoff]'))
        self.assertEqual(self.chat._pending_handoff['role'], 'assistant')
        self.assertEqual(writer.current_run.status, 'paused')
        self.assertEqual(self.chat.current_run.status, 'running')

    def test_handoff_to_run_id(self):
        self.chat.provider.chat.side_effect = [
            [{'type': 'token', 'content': 'Draft ready.'},
             {'type': 'done', 'reason': 'stop'}],
        ]
        self.chat.run_subagent('writer', 'draft it')
        child = [r for r in self.chat.runs.runs() if r.role == 'writer'][-1]
        self._handoff(f'#{child.id}')
        self.assertEqual(self.chat._pending_handoff['role'], 'writer')

    def test_handoff_to_child(self):
        self.chat.provider.chat.side_effect = [
            [{'type': 'token', 'content': 'Draft ready.'},
             {'type': 'done', 'reason': 'stop'}],
        ]
        self.chat.run_subagent('writer', 'draft it')
        self._handoff('child')
        self.assertEqual(self.chat._pending_handoff['role'], 'writer')

    def test_handoff_to_sibling(self):
        writer = self.chat.focus.focus_role('writer')
        self.chat.focus.focus_role('editor')
        writer._init_tooling()
        out = writer._run_tool('handoff', {'target': 'sibling'})
        self.assertTrue(out.startswith('[handoff]'))
        self.assertEqual(self.chat._pending_handoff['role'], 'editor')

    def test_handoff_to_root_role(self):
        writer = self.chat.focus.focus_role('writer')
        writer._init_tooling()
        writer._run_tool('handoff', {'target': 'assistant'})
        self.assertEqual(self.chat._pending_handoff['role'], 'assistant')

    def test_sub_agent_without_focus_errors(self):
        sub = self.chat._new_sub_engine('writer', task='draft')
        sub._init_tooling()
        out = sub._run_tool('handoff', {'target': 'parent'})
        self.assertTrue(out.startswith('Error'))
        self.assertIsNone(self.chat._pending_handoff)


class TestHandoffTurnStop(unittest.TestCase):

    def setUp(self):
        self.chat = make_chat()
        self.chat._bind_assistant()

    def tearDown(self):
        self.chat._tmp.cleanup()

    def test_loop_stops_after_handoff(self):
        self.chat.provider.chat.side_effect = [
            [{'type': 'tool_calls', 'tool_calls': [
                {'id': 'call_1', 'type': 'function',
                 'function': {'name': 'handoff',
                              'arguments': json.dumps({'target': 'writer'})}},
            ]}],
            [{'type': 'token', 'content': 'should not run'},
             {'type': 'done', 'reason': 'stop'}],
        ]
        with patch('sys.stdout', new=io.StringIO()):
            self.chat._agent_loop()
        self.assertEqual(self.chat.provider.chat.call_count, 1)
        self.assertEqual(self.chat._pending_handoff['role'], 'writer')


class TestHandoffApply(unittest.TestCase):

    def setUp(self):
        self.chat = make_chat()
        self.chat._bind_assistant()

    def tearDown(self):
        self.chat._tmp.cleanup()

    def test_apply_focuses_role(self):
        self.chat._pending_handoff = {'role': 'writer', 'target': 'writer'}
        out = io.StringIO()
        with patch('sys.stdout', new=out):
            self.chat._apply_handoff()
        self.assertEqual(self.chat.active().role, 'writer')
        self.assertIsNone(self.chat._pending_handoff)
        self.assertIn('Focused:', out.getvalue())

    def test_apply_root_role_resets(self):
        self.chat.focus.focus_role('writer')
        self.chat._pending_handoff = {'role': 'assistant', 'target': 'assistant'}
        with patch('sys.stdout', new=io.StringIO()):
            self.chat._apply_handoff()
        self.assertIs(self.chat.active(), self.chat)

    def test_run_applies_pending_after_turn(self):
        self.chat.provider.chat.return_value = [
            {'type': 'tool_calls', 'tool_calls': [
                {'id': 'call_1', 'type': 'function',
                 'function': {'name': 'handoff',
                              'arguments': json.dumps({'target': 'writer'})}},
            ]},
        ]
        with patch('sys.stdout', new=io.StringIO()):
            with patch('replio.chat.input', side_effect=['hi', EOFError]):
                with patch('replio.chat.readline'):
                    self.chat.run()
        self.assertEqual(self.chat.active().role, 'writer')


if __name__ == '__main__':
    unittest.main()
