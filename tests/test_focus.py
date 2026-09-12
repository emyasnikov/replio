import io
import unittest
from unittest.mock import MagicMock, patch

from replio.chat import MAIN_PROMPT
from replio.focus import FocusManager

from tests.helpers import make_chat


class TestFocusManager(unittest.TestCase):

    def setUp(self):
        self.chat = make_chat()
        self.chat._bind_assistant()
        self.focus = self.chat.focus

    def tearDown(self):
        self.chat._tmp.cleanup()

    def test_starts_at_root(self):
        self.assertIs(self.focus.active, self.chat)
        self.assertTrue(self.focus.is_root())
        self.assertEqual(self.focus.stack(), [self.chat])

    def test_focus_role_creates_stable_engine(self):
        engine = self.focus.focus_role('writer')
        self.assertIs(self.focus.active, engine)
        self.assertFalse(self.focus.is_root())
        self.assertEqual(engine.role, 'writer')
        self.assertEqual(engine.current_session.name, 'agent_writer')
        self.assertIs(engine._ui, self.chat._ui)
        self.assertIs(self.chat._ui._loop, engine)

    def test_refocus_returns_same_engine(self):
        first = self.focus.focus_role('writer')
        second = self.focus.focus_role('writer')
        self.assertIs(first, second)
        self.assertEqual(self.focus.stack(), [self.chat, first])

    def test_back_walks_the_stack(self):
        writer = self.focus.focus_role('writer')
        editor = self.focus.focus_role('editor')
        self.assertIs(self.focus.back(), writer)
        self.assertIs(self.focus.back(), self.chat)
        self.assertTrue(self.focus.is_root())
        self.assertIs(self.chat._ui._loop, self.chat)

    def test_focus_root_role_resets(self):
        self.focus.focus_role('writer')
        self.assertIs(self.focus.focus_role('assistant'), self.chat)
        self.assertTrue(self.focus.is_root())

    def test_unknown_role_raises(self):
        with self.assertRaises(ValueError):
            self.focus.focus_role('ghost')

    def test_find_and_engines(self):
        writer = self.focus.focus_role('writer')
        engines = self.focus.engines()
        self.assertEqual(engines[0], self.chat)
        self.assertIn(writer, engines)
        self.assertIs(self.focus.find('writer'), writer)
        self.assertIs(self.focus.find('editor'), None)

    def test_focused_engine_records_run(self):
        engine = self.chat.focused_engine('writer', ui=self.chat._ui)
        self.assertEqual(engine.current_run.role, 'writer')
        self.assertEqual(engine.current_run.parent, self.chat.current_run.id)
        self.assertEqual(engine.current_session.role, 'writer')
        self.assertEqual(engine.current_session.parent_id, '')


class TestFocusRouting(unittest.TestCase):

    def setUp(self):
        self.chat = make_chat()
        self.chat._bind_assistant()

    def tearDown(self):
        self.chat._tmp.cleanup()

    def _run(self, lines):
        out = io.StringIO()
        with patch('sys.stdout', new=out):
            with patch('replio.chat.input', side_effect=lines):
                with patch('replio.chat.readline'):
                    self.chat.run()
        return out.getvalue()

    def test_turn_routes_to_active_engine(self):
        engine = self.chat.focus.focus_role('writer')
        engine.chat = MagicMock()
        self.chat.chat = MagicMock()
        self._run(['hello', EOFError])
        engine.chat.assert_called_once_with('hello')
        self.chat.chat.assert_not_called()

    def test_command_routes_to_active_registry(self):
        engine = self.chat.focus.focus_role('writer')
        engine.registry = MagicMock()
        self.chat.registry = MagicMock()
        self._run(['/sessions list', EOFError])
        engine.registry.dispatch.assert_called_once_with('/sessions list')
        self.chat.registry.dispatch.assert_not_called()

    def test_prompt_shows_role_when_enabled(self):
        self.assertEqual(self.chat._prompt(), MAIN_PROMPT)
        self.chat.config.set('prompt_role', True)
        self.assertIn('Assistant >>>', self.chat._prompt())
        self.chat.focus.focus_role('writer')
        self.assertIn('Writer >>>', self.chat._prompt())

    def test_prompt_default_has_no_role(self):
        self.chat.focus.focus_role('writer')
        self.assertEqual(self.chat._prompt(), MAIN_PROMPT)


if __name__ == '__main__':
    unittest.main()
