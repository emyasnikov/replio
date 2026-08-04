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
        self.assertIn('run_command', output)
        self.assertIn('[exec · bash: ask]', output)
        self.assertIn('[read · read: allow]', output)

    def test_help_tool_detail(self):
        output = self._dispatch('/help read_file')
        self.assertIn('category: read', output)
        self.assertIn('path (required)', output)
        self.assertIn('offset (optional)', output)

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


if __name__ == '__main__':
    unittest.main()
