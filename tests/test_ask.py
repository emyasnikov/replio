import io
import json
import unittest
from unittest.mock import patch

from replio.types import AgentType

from tests.helpers import make_chat
from tests.test_engine import make_engine


class TestAskTool(unittest.TestCase):

    def setUp(self):
        self.chat = make_chat()
        self.sessions_dir = self.chat.config.local_path.parent / 'sessions'

    def tearDown(self):
        self.chat._tmp.cleanup()

    def _ask_call(self, question='which port?', **extra):
        args = {'question': question}
        args.update(extra)
        return [{
            'id': 'call_ask001',
            'type': 'function',
            'function': {'name': 'ask', 'arguments': json.dumps(args)},
        }]

    def _tool_msgs(self):
        return [m for m in self.chat.current_session.messages
                if m['role'] == 'tool']

    def test_ask_registered_in_schema(self):
        schema = self.chat._init_tooling()
        names = [s['function']['name'] for s in schema]
        self.assertIn('ask', names)
        entry = self.chat._tool_registry.info('ask')
        self.assertEqual(entry['category'], 'ask')
        self.assertEqual(entry['permission'], 'ask')
        params = entry['parameters']['properties']
        self.assertIn('question', params)
        self.assertIn('context', params)
        self.assertIn('options', params)
        self.assertIn('target', params)

    def test_human_ask_returns_answer(self):
        self.chat._init_tooling()
        with patch('builtins.input', return_value='Use port 8080'):
            out = self.chat._run_tool('ask', {'question': 'which port?'})
        self.assertEqual(out, 'Use port 8080')

    def test_human_ask_empty_is_cancelled(self):
        self.chat._init_tooling()
        with patch('builtins.input', return_value=''):
            out = self.chat._run_tool('ask', {'question': 'which port?'})
        self.assertIn('[cancelled]', out)
        self.assertIn('decide autonomously', out)

    def test_human_ask_context_and_options_presented(self):
        ui = self.chat._ask_ui
        with patch('builtins.input', return_value='b'):
            with patch('sys.stdout', new=io.StringIO()) as buf:
                result = ui.ask('which?', context='ctx',
                                options=['a', 'b'], origin=self.chat.current_session.name)
        self.assertEqual(result, 'b')
        out = buf.getvalue()
        self.assertIn('Ask: which?', out)
        self.assertIn('ctx', out)
        self.assertIn('Options: a / b', out)

    def test_ask_no_ui_no_lead_errors(self):
        engine = make_engine()
        try:
            engine._init_tooling()
            out = engine._run_tool('ask', {'question': 'q'})
            self.assertIn('Error: ask has no one to answer', out)
        finally:
            engine._tmp.cleanup()

    def test_lead_target_consults_lead_model(self):
        self.chat.types.put(
            AgentType(name='w', system_prompt='Writer agent'), scope='local')
        sub = self.chat._new_sub_engine('w')
        self.assertIs(sub._lead, self.chat)
        self.assertIs(sub._ask_ui, self.chat._ask_ui)
        self.chat.provider.chat_nonstreaming.return_value = {
            'content': 'Proceed with B'}
        sub._init_tooling()
        out = sub._run_tool('ask', {'question': 'which option?',
                                    'target': 'lead'})
        self.assertEqual(out, 'Proceed with B')
        self.chat.provider.chat_nonstreaming.assert_called_once()
        msgs = self.chat.provider.chat_nonstreaming.call_args.args[0]
        self.assertIn('which option?', msgs[-1]['content'])

    def test_lead_target_falls_back_to_human_when_lead_silent(self):
        self.chat.types.put(
            AgentType(name='w', system_prompt='Writer agent'), scope='local')
        sub = self.chat._new_sub_engine('w')
        self.chat.provider.chat_nonstreaming.return_value = {'content': None}
        sub._init_tooling()
        with patch('builtins.input', return_value='from human'):
            out = sub._run_tool('ask', {'question': 'q', 'target': 'lead'})
        self.assertEqual(out, 'from human')

    def test_lead_target_at_root_falls_back_to_human(self):
        self.chat._init_tooling()
        self.assertIsNone(self.chat._lead)
        with patch('builtins.input', return_value='operator decision'):
            out = self.chat._run_tool('ask', {'question': 'q', 'target': 'lead'})
        self.assertEqual(out, 'operator decision')

    def test_full_loop_persists_answer_and_continues(self):
        self.chat.provider.chat.side_effect = [
            [{'type': 'tool_calls', 'tool_calls': self._ask_call()}],
            [{'type': 'token', 'content': 'Final answer.'},
             {'type': 'done', 'reason': 'stop'}],
        ]
        with patch('builtins.input', return_value='Use 8080'):
            with patch('sys.stdout', new=io.StringIO()):
                self.chat._agent_loop()
        tools = self._tool_msgs()
        self.assertEqual(len(tools), 1)
        self.assertIn('Use 8080', tools[0]['content'])
        self.assertEqual(self.chat.provider.chat.call_count, 2)


if __name__ == '__main__':
    unittest.main()
