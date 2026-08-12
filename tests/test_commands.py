import unittest
import io
from unittest.mock import patch

from tests.helpers import make_chat


class TestToolCommand(unittest.TestCase):

    def setUp(self):
        self.chat = make_chat()

    def tearDown(self):
        self.chat._tmp.cleanup()

    def _dispatch(self, line):
        out = io.StringIO()
        with patch('sys.stdout', new=out):
            self.chat.registry.dispatch(line)
        return out.getvalue()

    def test_tool_lists_names_without_args(self):
        output = self._dispatch('/tool')
        self.assertIn('web_search', output)
        self.assertIn('fetch_page', output)

    def test_help_lists_aliases_inline(self):
        output = self._dispatch('/help')
        self.assertIn('/help, /h', output)
        self.assertIn('/exit, /quit, /q', output)
        self.assertNotIn('aliases:', output)

    def test_help_shows_subcommands(self):
        output = self._dispatch('/help')
        self.assertIn('new', output)
        self.assertIn('Start a new session', output)
        self.assertIn('load', output)
        self.assertIn('List saved sessions', output)

    def test_help_subcommand_indent(self):
        output = self._dispatch('/help')
        self.assertIn('\n    new', output)

    def test_help_shows_tools_section(self):
        output = self._dispatch('/help')
        self.assertIn('Available tools:', output)
        self.assertIn('Run a shell command', output)
        self.assertIn('Find files matching a glob pattern', output)
        self.assertNotIn('[exec · bash: ask]', output)

    def test_help_tool_detail(self):
        output = self._dispatch('/help read_file')
        self.assertIn('category: read', output)
        self.assertIn('path (required)', output)
        self.assertIn('offset (optional)', output)

    def test_help_tool_detail_has_permission(self):
        output = self._dispatch('/help run_command')
        self.assertIn('category: exec', output)
        self.assertIn('permission: bash: ask', output)
        self.assertIn('command (required)', output)

    def test_help_command_by_name(self):
        output = self._dispatch('/help session')
        self.assertIn('Start a new session', output)

    def test_help_alias_resolution(self):
        output = self._dispatch('/help h')
        self.assertIn('Show available commands and tools', output)

    def test_help_unknown(self):
        output = self._dispatch('/help nosuch')
        self.assertIn('No help available for "nosuch"', output)

    def test_tool_listing_points_to_help(self):
        output = self._dispatch('/tool')
        self.assertIn('Use /help <tool> for details', output)
        self.assertNotIn(', web_search', output)

    def test_session_no_args_shows_subcommands(self):
        output = self._dispatch('/session')
        self.assertIn('Start a new session', output)
        self.assertIn('Delete a session', output)

    def test_session_new_switches_current_session(self):
        old = self.chat.current_session
        self._dispatch('/session new')
        self.assertIsNot(self.chat.current_session, old)
        self.assertEqual(self.chat.current_session.messages, [])

    def test_session_load_switches_current_session(self):
        old = self.chat.current_session
        s = self.chat.sessions.create('saved1')
        s.add_message('user', 'hello from saved session')
        self.chat.sessions.save(s)
        self._dispatch('/session load saved1')
        self.assertIsNot(self.chat.current_session, old)
        self.assertEqual([m['content'] for m in self.chat.current_session.messages],
                         ['hello from saved session'])

    def test_session_load_shows_context_size(self):
        s = self.chat.sessions.create('saved2')
        s.add_message('user', 'hello world')
        self.chat.sessions.save(s)
        output = self._dispatch('/session load saved2')
        self.assertIn('1 messages', output)
        self.assertIn('context', output)

    def test_session_load_not_found(self):
        output = self._dispatch('/session load nosuch')
        self.assertIn('Session not found: nosuch', output)

    def test_session_load_offers_compact_when_large(self):
        s = self.chat.sessions.create('big1')
        for i in range(20):
            s.add_message('user', 'x' * 2000)
        self.chat.sessions.save(s)
        self.chat.compact_session = unittest.mock.MagicMock()
        with patch('replio.commands.builtins.input', return_value='y'):
            self._dispatch('/session load big1')
        self.chat.compact_session.assert_called_once()

    def test_compact_dispatch_calls_compaction(self):
        self.chat.compact_session = unittest.mock.MagicMock()
        self._dispatch('/compact')
        self.chat.compact_session.assert_called_once()

    def test_config_parses_json_list(self):
        self._dispatch('/config tools.deny ["run_command", "web_search"]')
        self.assertEqual(self.chat.config.get('tools.deny'),
                         ['run_command', 'web_search'])

    def test_config_parses_numbers(self):
        self._dispatch('/config temperature 0.3')
        self._dispatch('/config max_tokens 4096')
        self.assertEqual(self.chat.config.get('temperature'), 0.3)
        self.assertEqual(self.chat.config.get('max_tokens'), 4096)

    def test_config_add_item(self):
        self.chat.config.set('tools.deny', ['run_command'])
        self._dispatch('/config tools.deny -a write_file')
        self.assertIn('write_file', self.chat.config.get('tools.deny'))

    def test_config_add_creates_list(self):
        self._dispatch('/config tools.deny -a run_command')
        self.assertEqual(self.chat.config.get('tools.deny'), ['run_command'])

    def test_config_remove_item(self):
        self.chat.config.set('tools.deny', ['run_command', 'write_file'])
        self._dispatch('/config tools.deny -r run_command')
        self.assertNotIn('run_command', self.chat.config.get('tools.deny'))

    def test_config_unknown_key_prompts(self):
        with patch('replio.commands.builtins.input', return_value='y'):
            self._dispatch('/config frobnicate 1')
        self.assertEqual(self.chat.config.get('frobnicate'), 1)

    def test_config_unknown_key_declined(self):
        with patch('replio.commands.builtins.input', return_value='n'):
            output = self._dispatch('/config frobnicate 1')
        self.assertIn('Skipped', output)
        self.assertIsNone(self.chat.config.get('frobnicate'))

    def test_config_instances_do_not_share_lists(self):
        self._dispatch('/config tools.deny -a run_command')
        other = make_chat()
        try:
            self.assertEqual(other.config.get('tools.deny'), [])
        finally:
            other._tmp.cleanup()

    def test_tool_executes_via_registry(self):
        with patch('replio.web.search.search', return_value=[
            {'title': 'T', 'url': 'http://x.com', 'snippet': 'S'}
        ]) as search_mock:
            output = self._dispatch('/tool web_search {"query": "python news"}')
        search_mock.assert_called_once_with('python news')
        self.assertIn('python news', output)

    def test_tool_disabled_when_tool_calling_off(self):
        self.chat.config.set('tool_calling', False)
        output = self._dispatch('/tool web_search {"query": "x"}')
        self.assertIn('disabled', output)

    def test_tool_invalid_json(self):
        output = self._dispatch('/tool web_search not-json')
        self.assertIn('Usage: /tool', output)

    def test_tool_denied_by_policy(self):
        self.chat.config.set('tools.deny', ['web_search'])
        output = self._dispatch('/tool web_search {"query": "x"}')
        self.assertIn('disabled by tool policy', output)

    def test_tool_listing_respects_deny(self):
        self.chat.config.set('tools.deny', ['web_search'])
        output = self._dispatch('/tool')
        self.assertNotIn('web_search', output)
        self.assertIn('read_file', output)

    def test_tool_ask_prompt_declined(self):
        self.chat.config.set('tool_permission', {'web': 'ask'})
        with patch('replio.chat.input', return_value='n'):
            output = self._dispatch('/tool web_search {"query": "x"}')
        self.assertIn('[cancelled]', output)

    def test_tool_ask_prompt_accepted(self):
        self.chat.config.set('tool_permission', {'web': 'ask'})
        with patch('replio.web.search.search', return_value=[
            {'title': 'T', 'url': 'http://x.com', 'snippet': 'S'}
        ]), patch('replio.chat.input', return_value='y'):
            output = self._dispatch('/tool web_search {"query": "python"}')
        self.assertNotIn('[cancelled]', output)
        self.assertIn('python', output)

    def test_schema_filters_denied_tools(self):
        self.chat.config.set('tools.deny', ['web_search', 'run_command'])
        schema = self.chat._init_tooling()
        names = [s['function']['name'] for s in schema]
        self.assertNotIn('web_search', names)
        self.assertNotIn('run_command', names)
        self.assertIn('read_file', names)


class TestReadlineCompleter(unittest.TestCase):

    def setUp(self):
        self.chat = make_chat()

    def tearDown(self):
        self.chat._tmp.cleanup()

    def _buffer(self, line):
        return patch('replio.chat.readline.get_line_buffer', return_value=line)

    def _make_sessions(self, *names):
        for n in names:
            s = self.chat.sessions.create(n)
            s.add_message('user', 'x')
            self.chat.sessions.save(s)

    def test_session_load_completes_names(self):
        self._make_sessions('alpha_01', 'alpha_02', 'beta_01')
        with self._buffer('/session load alpha_'):
            self.assertEqual(self.chat._completer('alpha_', 0), 'alpha_01 ')
            self.assertEqual(self.chat._completer('alpha_', 1), 'alpha_02 ')
            self.assertIsNone(self.chat._completer('alpha_', 2))

    def test_session_delete_completes_names(self):
        self._make_sessions('alpha_01')
        with self._buffer('/session delete alpha_'):
            self.assertEqual(self.chat._completer('alpha_', 0), 'alpha_01 ')
            self.assertIsNone(self.chat._completer('alpha_', 1))

    def test_session_load_empty_prefix_lists_all(self):
        self._make_sessions('alpha_01', 'beta_01')
        with self._buffer('/session load '):
            matches = []
            i = 0
            while True:
                m = self.chat._completer('', i)
                if m is None:
                    break
                matches.append(m)
                i += 1
        self.assertEqual(matches, ['alpha_01 ', 'beta_01 '])

    def test_command_completion_still_works(self):
        with self._buffer('/se'):
            self.assertEqual(self.chat._completer('/se', 0), '/session ')

    def test_command_completion_without_slash_prefix(self):
        with self._buffer('/se'):
            self.assertEqual(self.chat._completer('se', 0), 'session ')

    def test_command_completion_outside_session_context(self):
        with self._buffer('/session'):
            self.assertEqual(self.chat._completer('/session', 0), '/session ')


if __name__ == '__main__':
    unittest.main()
