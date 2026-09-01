import io
import sys
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

    def test_repl_tool_error_renders_first_line(self):
        out = io.StringIO()
        with patch('sys.stdout', new=out):
            self.chat._ui.tool_error('Error: boom\nsecond line')
        value = out.getvalue()
        self.assertIn('! Error: boom', value)
        self.assertNotIn('second line', value)

    def test_headless_tool_error_renders_when_verbose(self):
        ui = HeadlessUI(auto='deny', verbose=True)
        err = io.StringIO()
        with patch('sys.stderr', new=err):
            ui.tool_error('Error: boom')
        self.assertIn('! Error: boom', err.getvalue())

    def test_headless_tool_error_silent_when_not_verbose(self):
        ui = HeadlessUI(auto='deny', verbose=False)
        err = io.StringIO()
        with patch('sys.stderr', new=err):
            ui.tool_error('Error: boom')
        self.assertEqual(err.getvalue(), '')

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

    def test_thinking_end_streamed_prints_thought_duration(self):
        self.chat.config.set('show_thinking', True)
        self.chat.config.set('show_thought_duration', True)
        out = io.StringIO()
        with patch('sys.stdout', new=out):
            self.chat._ui.thinking_end(2.5)
        value = out.getvalue()
        self.assertIn('(Thought 2.5s)', value)
        self.assertNotIn('+ Thought', value)

    def test_thinking_end_streamed_hides_thought_duration_when_off(self):
        self.chat.config.set('show_thinking', True)
        self.chat.config.set('show_thought_duration', False)
        out = io.StringIO()
        with patch('sys.stdout', new=out):
            self.chat._ui.thinking_end(1.0)
        self.assertNotIn('Thought', out.getvalue())


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


class TestWordStreaming(unittest.TestCase):

    PREFIX = '\001\033[33m\002<<< \001\033[0m\002'

    def setUp(self):
        self.chat = make_chat()
        self.ui = self.chat._ui

    def tearDown(self):
        self.chat._tmp.cleanup()

    def _capture(self, fn):
        out = io.StringIO()
        with patch('sys.stdout', new=out):
            fn()
        return out.getvalue()

    def test_word_streaming_default_true(self):
        from replio.config import DEFAULT_CONFIG
        self.assertTrue(DEFAULT_CONFIG['word_streaming'])

    def test_partial_word_held_until_boundary(self):
        def run():
            self.ui.token('app')
            self.ui.token('rox ')
            self.ui.token('hard')
        value = self._capture(run)
        self.assertEqual(value, self.PREFIX + 'approx ')
        self.assertEqual(self.ui._word_buffer, 'hard')

    def test_flush_writes_remainder(self):
        def run():
            self.ui.token('app')
            self.ui.token('rox ')
            self.ui.token('hard')
            self.ui.flush()
        value = self._capture(run)
        self.assertEqual(value, self.PREFIX + 'approx hard')
        self.assertEqual(self.ui._word_buffer, '')

    def test_multi_word_token_flushes_through_last_space(self):
        def run():
            self.ui.token('word1 word2 par')
        value = self._capture(run)
        self.assertEqual(value, self.PREFIX + 'word1 word2 ')
        self.assertEqual(self.ui._word_buffer, 'par')

    def test_newline_flushes(self):
        def run():
            self.ui.token('line1\n')
            self.ui.token('par')
        value = self._capture(run)
        self.assertEqual(value, self.PREFIX + 'line1\n')
        self.assertEqual(self.ui._word_buffer, 'par')

    def test_footer_flushes_tail(self):
        def run():
            self.ui.token('hard')
            self.ui.footer(3.0, {'context': 10})
        value = self._capture(run)
        self.assertIn('hard', value)
        self.assertIn('(3.0s, 10 tokens)', value)
        self.assertIn('hard\n', value)
        self.assertLess(value.index('hard'), value.index('(3.0s'))

    def test_footer_token_parts_selected(self):
        self.chat.config.set('footer_tokens', ['in', 'thinking', 'out'])
        def run():
            self.ui.footer(3.0, {'in': 12, 'thinking': 5, 'out': 8})
        value = self._capture(run)
        self.assertIn('(3.0s, 12t/5t/8t)', value)

    def test_footer_token_parts_skip_unavailable(self):
        self.chat.config.set('footer_tokens', ['in', 'thinking', 'out'])
        def run():
            self.ui.footer(3.0, {'in': 12})
        value = self._capture(run)
        self.assertIn('(3.0s, 12t)', value)
        self.assertNotIn('thinking', value)

    def test_footer_token_parts_empty_hides_tokens(self):
        self.chat.config.set('footer_tokens', [])
        def run():
            self.ui.footer(3.0, {'context': 10})
        value = self._capture(run)
        self.assertIn('(3.0s)', value)
        self.assertNotIn('tokens', value)

    def test_footer_show_context_size_off_hides_tokens(self):
        self.chat.config.set('show_context_size', False)
        self.chat.config.set('footer_tokens', ['in', 'out'])
        def run():
            self.ui.footer(3.0, {'in': 12, 'out': 8})
        value = self._capture(run)
        self.assertIn('(3.0s)', value)
        self.assertNotIn('t', value)

    def test_word_streaming_off_writes_immediately(self):
        self.chat.config.set('word_streaming', False)

        def run():
            self.ui.token('app')
            self.ui.token('rox ')
        self.assertEqual(self._capture(run), self.PREFIX + 'approx ')
        self.assertEqual(self.ui._word_buffer, '')

    def test_markdown_bold_across_flush_boundary(self):
        self.chat.config.set('markdown_streaming', True)

        def run():
            self.ui.token('**bo')
            self.ui.token('ld**: ok')
            self.ui.flush()
        value = self._capture(run)
        self.assertIn('bold', value)
        self.assertNotIn('*', value)

    def test_activity_flushes_pending_word(self):
        def run():
            self.ui.token('par')
            self.ui.activity('→', 'Write', 'a.md', ['+ hi'])
        value = self._capture(run)
        self.assertIn('par', value)
        self.assertIn('→ Write a.md', value)
        self.assertLess(value.index('par'), value.index('→ Write a.md'))

    def test_confirm_flushes_pending_word(self):
        def fake_input(prompt):
            sys.stdout.write(prompt)
            return 'n'

        def run():
            self.ui.token('par')
            with patch('replio.ui.input', side_effect=fake_input):
                self.ui.confirm('write_file', 'write_file a.md')
        value = self._capture(run)
        self.assertIn('par', value)
        self.assertIn('write_file a.md', value)
        self.assertLess(value.index('par'), value.index('write_file a.md'))

    def test_confirm_question_marks_start_of_line(self):
        def fake_input(prompt):
            sys.stdout.write(prompt)
            return 'n'

        def run():
            with patch('replio.ui.input', side_effect=fake_input):
                self.ui.confirm('write_file', 'write_file a.md')
        value = self._capture(run)
        self.assertIn('? write_file a.md - approve? [y/N]', value)
        self.assertNotIn('  ? ', value)

    def test_confirm_raises_on_keyboard_interrupt(self):
        def fake_input(prompt):
            raise KeyboardInterrupt()

        with patch('replio.ui.input', side_effect=fake_input):
            with self.assertRaises(KeyboardInterrupt):
                self.ui.confirm('write_file', 'write_file a.md')

    def test_confirm_returns_false_on_eof(self):
        def fake_input(prompt):
            raise EOFError()

        with patch('replio.ui.input', side_effect=fake_input):
            self.assertFalse(self.ui.confirm('write_file', 'write_file a.md'))


if __name__ == '__main__':
    unittest.main()
