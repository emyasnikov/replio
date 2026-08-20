import io
import unittest
from unittest.mock import patch

from tests.helpers import make_chat
from replio.engine import Engine
from replio.ui import HeadlessUI


class TestGlyphActivityLines(unittest.TestCase):

    def setUp(self):
        self.chat = make_chat()
        self.chat._init_tooling()
        self.chat._show_tool_status = Engine._show_tool_status.__get__(self.chat)

    def tearDown(self):
        self.chat._tmp.cleanup()

    def _capture_status(self, name, args):
        out = io.StringIO()
        with patch('sys.stdout', new=out):
            self.chat._show_tool_status(name, args)
        return out.getvalue()

    def test_glyph_lines_default_true(self):
        from replio.config import DEFAULT_CONFIG
        self.assertTrue(DEFAULT_CONFIG['glyph_lines'])

    def test_repl_activity_renders_glyph_line(self):
        out = io.StringIO()
        with patch('sys.stdout', new=out):
            self.chat._ui.activity('→', 'Write', 'a.md', ['+ hi'])
        value = out.getvalue()
        self.assertIn('→ Write a.md', value)
        self.assertIn('+ hi', value)

    def test_headless_activity_renders_when_verbose(self):
        ui = HeadlessUI(auto='deny', verbose=True)
        err = io.StringIO()
        with patch('sys.stderr', new=err):
            ui.activity('$', 'Run', 'echo hi', [])
        self.assertIn('$ Run echo hi', err.getvalue())

    def test_status_renders_glyph_when_mapped(self):
        value = self._capture_status('write_file', {'path': 'a.md', 'content': 'x'})
        self.assertIn('→ Write a.md', value)
        self.assertNotIn('[write_file:', value)

    def test_status_falls_back_to_oneliner_when_disabled(self):
        self.chat.config.set('glyph_lines', False)
        value = self._capture_status('write_file', {'path': 'a.md', 'content': 'x'})
        self.assertIn('[write_file: a.md]', value)
        self.assertNotIn('→', value)

    def test_status_falls_back_to_oneliner_for_unmapped_category(self):
        params = {'type': 'object', 'properties': {}, 'required': []}
        self.chat._tool_registry.register(
            'xyz_case', 'Do something', params, category='custom')(lambda: 'ok')
        value = self._capture_status('xyz_case', {})
        self.assertIn('[xyz_case: xyz_case]', value)


class TestThinkingSpinner(unittest.TestCase):

    def setUp(self):
        self.chat = make_chat()

    def tearDown(self):
        self.chat._ui._stop_spinner()
        self.chat._tmp.cleanup()

    def test_spinner_starts_when_thinking_hidden(self):
        self.chat.config.set('show_thinking', False)
        self.chat._ui.thinking_begin()
        self.assertIsNotNone(self.chat._ui._spinner_thread)
        self.assertTrue(self.chat._ui._spinner_thread.is_alive())

    def test_no_spinner_when_thinking_visible(self):
        self.chat.config.set('show_thinking', True)
        self.chat._ui.thinking_begin()
        self.assertIsNone(self.chat._ui._spinner_thread)

    def test_thinking_end_stops_spinner_and_prints_thought(self):
        self.chat.config.set('show_thinking', False)
        self.chat._ui.thinking_begin()
        thread = self.chat._ui._spinner_thread
        out = io.StringIO()
        with patch('sys.stdout', new=out):
            self.chat._ui.thinking_end(2.5)
        self.assertFalse(thread.is_alive())
        self.assertIsNone(self.chat._ui._spinner_thread)
        value = out.getvalue()
        self.assertIn('\r\033[K', value)
        self.assertIn('+ Thought 2.5s', value)

    def test_thinking_end_without_spinner_is_clean(self):
        self.chat.config.set('show_thinking', False)
        out = io.StringIO()
        with patch('sys.stdout', new=out):
            self.chat._ui.thinking_end(1.0)
        self.assertIsNone(self.chat._ui._spinner_thread)
        self.assertIn('+ Thought 1.0s', out.getvalue())


class TestEphemeralUI(unittest.TestCase):

    def test_activity_lines_not_persisted_to_session(self):
        chat = make_chat()
        chat._init_tooling()
        chat._show_tool_status = Engine._show_tool_status.__get__(chat)
        chat._show_tool_status('write_file', {'path': 'a.md', 'content': 'x'})
        dump = chat.current_session.to_dict()
        blob = str(dump)
        self.assertNotIn('→ Write a.md', blob)
        self.assertNotIn('[write_file: a.md]', blob)
        chat._tmp.cleanup()


if __name__ == '__main__':
    unittest.main()
