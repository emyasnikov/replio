import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from replio.personas import Persona
from replio.ui import NullUI

from tests.helpers import make_chat


class TestSubAgentEngine(unittest.TestCase):

    def setUp(self):
        self.tmp = MagicMock()
        self.chat = make_chat()
        self.sessions_dir = self.chat.config.local_path.parent / 'sessions'

    def tearDown(self):
        self.chat._tmp.cleanup()

    def _delegate_log(self, persona):
        files = sorted(self.sessions_dir.glob(f'delegate_{persona}_*.json'))
        self.assertTrue(files, f'no delegate_{persona} session saved')
        return json.loads(files[-1].read_text())

    def _tool_call(self, name='run_command', args='{"command": "echo hi"}'):
        return [{
            'id': 'call_sub001',
            'type': 'function',
            'function': {'name': name, 'arguments': args},
        }]

    def test_subagent_inherits_provider_and_plugins(self):
        sub = self.chat._new_sub_engine('writer')
        self.assertIs(sub.provider, self.chat.provider)
        self.assertIs(sub._plugin_manager, self.chat._plugin_manager)
        self.assertTrue(sub.current_session.name.startswith('delegate_writer'))

    def test_subagent_applies_persona_prompt_mode_permissions(self):
        sub = self.chat._new_sub_engine('writer')
        self.assertEqual(sub.config.get('mode'), 'build')
        self.assertTrue(sub.config.get('system_prompt').startswith(
            'You are the writer.'))
        tp = sub.config.get('tool_permission')
        self.assertEqual(tp['edit'], 'allow')
        self.assertEqual(tp['bash'], 'deny')
        self.assertEqual(tp['web'], 'deny')

    def test_subagent_uses_null_ui(self):
        sub = self.chat._new_sub_engine('writer')
        self.assertIsInstance(sub.ui, NullUI)

    def test_model_override_applies(self):
        self.chat.personas.put(
            Persona(name='special', system_prompt='sp', model='deepseek-r1'),
            scope='local')
        sub = self.chat._new_sub_engine('special')
        self.assertEqual(sub.config.get('model'), 'deepseek-r1')
        self.assertEqual(sub.provider.model, 'deepseek-r1')

    def test_inherits_shared_worktree(self):
        sub = self.chat._new_sub_engine('writer')
        self.assertEqual(sub.config.local_path.parent.parent,
                         self.chat.config.local_path.parent.parent)

    def test_unknown_persona_raises(self):
        with self.assertRaises(ValueError):
            self.chat._new_sub_engine('nope')

    def test_run_subagent_returns_result_and_persists(self):
        self.chat.provider.chat.side_effect = [
            [{'type': 'token', 'content': 'Draft ready.'},
             {'type': 'done', 'reason': 'stop'}],
        ]
        result = self.chat.run_subagent('writer', 'write the doc')
        self.assertEqual(result.content, 'Draft ready.')
        self.assertTrue(result.session.startswith('delegate_writer'))
        data = self._delegate_log('writer')
        self.assertEqual(data['messages'][0]['role'], 'user')
        self.assertEqual(data['messages'][-1]['role'], 'assistant')
        self.assertEqual(data['messages'][-1]['content'], 'Draft ready.')

    def test_run_subagent_unknown_persona_raises(self):
        with self.assertRaises(ValueError):
            self.chat.run_subagent('nope', 'anything')

    def test_ask_gated_tool_cancelled_without_prompt(self):
        self.chat.personas.put(
            Persona(name='defaults', system_prompt='plain agent'),
            scope='local')
        self.chat.provider.chat.side_effect = [
            [{'type': 'tool_calls', 'tool_calls': self._tool_call()}],
            [{'type': 'token', 'content': 'final'},
             {'type': 'done', 'reason': 'stop'}],
        ]
        result = self.chat.run_subagent('defaults', 'run the build')
        self.assertEqual(self.chat.provider.chat.call_count, 2)
        data = self._delegate_log('defaults')
        tools = [m for m in data['messages'] if m['role'] == 'tool']
        self.assertTrue(tools)
        self.assertIn('[cancelled]', tools[0]['content'])
        self.assertEqual(result.content, 'final')


if __name__ == '__main__':
    unittest.main()