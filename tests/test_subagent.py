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
        files = sorted(
            f for f in self.sessions_dir.glob('sub_*.json')
            if json.loads(f.read_text()).get('parent_id')
            == self.chat.current_session.name)
        self.assertTrue(files,
                        f'no sub_* child of {self.chat.current_session.name} saved')
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
        self.assertTrue(sub.current_session.name.startswith('sub_'))
        self.assertTrue(sub.current_session.name.endswith(
            f'_{self.chat.current_session.name}'))
        self.assertEqual(sub.current_session.parent_id,
                         self.chat.current_session.name)

    def test_sub_session_name_uses_parent_id(self):
        from replio.engine import _sub_session_name
        name = _sub_session_name('20260825_120000',
                                 'ses_20260825_110000_what_is_oee',
                                 self.sessions_dir)
        self.assertEqual(
            name, 'sub_20260825_120000_ses_20260825_110000_what_is_oee')

    def test_sub_session_name_sanitizes_and_truncates(self):
        from replio.engine import _sub_session_name
        name = _sub_session_name('20260825_120000', 'x' * 90, self.sessions_dir)
        self.assertLessEqual(len(name), 5 + 1 + 15 + 1 + 64)
        self.assertNotIn(' ', name)

    def test_sub_session_name_dedupes_collision(self):
        from replio.engine import _sub_session_name
        parent = 'ses_parent'
        (self.sessions_dir / 'sub_20260825_120000_ses_parent.json').write_text('{}')
        name = _sub_session_name('20260825_120000', parent, self.sessions_dir)
        self.assertEqual(name, 'sub_20260825_120000_ses_parent_2')

    def test_subagent_applies_persona_prompt_mode_permissions(self):
        sub = self.chat._new_sub_engine('writer')
        self.assertEqual(sub.config.get('mode'), 'build')
        self.assertTrue(sub.config.get('system_prompt').startswith(
            'You are the writer.'))
        tp = sub.config.get('tool_permission')
        self.assertEqual(tp['edit'], 'allow')
        self.assertEqual(tp['bash'], 'deny')
        self.assertEqual(tp['web'], 'deny')

    def test_subagent_injects_persona_skills(self):
        from replio.skills import Skill
        self.chat.personas.put(
            Persona(name='researcher', system_prompt='You are the researcher.',
                    skills=['finders', 'filters']),
            scope='local')
        self.chat.skills.put(
            Skill(name='finders', content='Find sources and evaluate them.'))
        self.chat.skills.put(
            Skill(name='filters', content='Filter for credible, on-topic sources.'))
        sub = self.chat._new_sub_engine('researcher')
        prompt = sub.config.get('system_prompt')
        self.assertIn('You are the researcher.', prompt)
        self.assertIn('## Skills', prompt)
        self.assertIn('### finders', prompt)
        self.assertIn('Find sources and evaluate them.', prompt)
        self.assertIn('### filters', prompt)

    def test_subagent_skips_missing_skills(self):
        from replio.skills import Skill
        self.chat.personas.put(
            Persona(name='x', system_prompt='prompt',
                    skills=['present', 'deleted']),
            scope='local')
        self.chat.skills.put(Skill(name='present', content='Present skill body.'))
        sub = self.chat._new_sub_engine('x')
        prompt = sub.config.get('system_prompt')
        self.assertIn('Present skill body.', prompt)
        self.assertNotIn('deleted', prompt)
        self.assertNotIn('## Skills\n\n### deleted', prompt)

    def test_subagent_without_skills_prompt_unchanged(self):
        self.chat.personas.put(
            Persona(name='plain', system_prompt='plain prompt', skills=[]),
            scope='local')
        sub = self.chat._new_sub_engine('plain')
        self.assertEqual(sub.config.get('system_prompt'), 'plain prompt')

    def test_subagent_skills_only_prompt(self):
        from replio.skills import Skill
        self.chat.personas.put(
            Persona(name='solo', system_prompt='', skills=['one']),
            scope='local')
        self.chat.skills.put(Skill(name='one', content='Skill only body.'))
        sub = self.chat._new_sub_engine('solo')
        prompt = sub.config.get('system_prompt')
        self.assertEqual(prompt, '## Skills\n\n### one\n\nSkill only body.')

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
        self.assertTrue(result.session.startswith('sub_'))
        self.assertTrue(result.session.endswith(f'_{self.chat.current_session.name}'))
        data = self._delegate_log('writer')
        self.assertEqual(data['messages'][0]['role'], 'user')
        self.assertEqual(data['messages'][-1]['role'], 'assistant')
        self.assertEqual(data['messages'][-1]['content'], 'Draft ready.')
        self.assertEqual(data['parent_id'], self.chat.current_session.name)
        self.assertIn(result.session, self.chat.current_session.sub_sessions)
        self.chat.sessions.save(self.chat.current_session)
        parent = self.chat.sessions.read(self.chat.current_session.name)
        self.assertIn(result.session, parent.sub_sessions)

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