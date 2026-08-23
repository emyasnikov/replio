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

    def _search_service(self):
        return self.chat._plugin_manager.service('search')

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

    def test_help_lists_tools_under_tool(self):
        output = self._dispatch('/help')
        self.assertNotIn('Available tools:', output)
        self.assertIn('\n    run_command', output)
        self.assertIn('Run a shell command', output)
        self.assertIn('Find files matching a glob pattern', output)
        self.assertNotIn('[exec · bash: ask]', output)

    def test_help_tool_shows_tool_rows(self):
        output = self._dispatch('/help tool')
        self.assertIn('\n    read_file', output)
        self.assertIn('Read the contents of a text file', output)

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
        with patch('replio.commands.builtins.input', return_value='n'):
            self._dispatch('/session load saved1')
        self.assertIsNot(self.chat.current_session, old)
        self.assertEqual([m['content'] for m in self.chat.current_session.messages],
                         ['hello from saved session', '/session load saved1'])

    def test_session_load_shows_context_size(self):
        s = self.chat.sessions.create('saved2')
        s.add_message('user', 'hello world')
        self.chat.sessions.save(s)
        with patch('replio.commands.builtins.input', return_value='n'):
            output = self._dispatch('/session load saved2')
        self.assertIn('1 messages', output)
        self.assertIn('context', output)

    def test_session_load_not_found(self):
        output = self._dispatch('/session load nosuch')
        self.assertIn('Session not found: nosuch', output)

    def test_session_load_offers_compact(self):
        s = self.chat.sessions.create('big1')
        s.add_message('user', 'x')
        self.chat.sessions.save(s)
        self.chat.compact_session = unittest.mock.MagicMock()
        with patch('replio.commands.builtins.input', return_value='y'):
            self._dispatch('/session load big1')
        self.chat.compact_session.assert_called_once()

    def test_session_load_declines_compact(self):
        s = self.chat.sessions.create('big2')
        s.add_message('user', 'x')
        self.chat.sessions.save(s)
        self.chat.compact_session = unittest.mock.MagicMock()
        with patch('replio.commands.builtins.input', return_value='n'):
            self._dispatch('/session load big2')
        self.chat.compact_session.assert_not_called()

    def test_session_preview_does_not_switch_current(self):
        old = self.chat.current_session
        s = self.chat.sessions.create('pv1')
        s.add_message('user', 'hello')
        s.add_message('assistant', None, tool_calls=[{
            'id': 'c1', 'type': 'function',
            'function': {'name': 'web_search', 'arguments': '{}'},
        }])
        self.chat.sessions.save(s)
        output = self._dispatch('/session preview pv1')
        self.assertIs(self.chat.current_session, old)
        self.assertIn('2 messages', output)
        self.assertIn('web_search', output)

    def test_session_preview_not_found(self):
        output = self._dispatch('/session preview nosuch')
        self.assertIn('Session not found: nosuch', output)

    def test_compact_dispatch_calls_compaction(self):
        self.chat.compact_session = unittest.mock.MagicMock()
        self._dispatch('/compact')
        self.chat.compact_session.assert_called_once()

    def test_version_prints_version(self):
        from replio import get_version
        output = self._dispatch('/version')
        self.assertIn(get_version(), output)

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
        with patch.object(self._search_service(), 'search', return_value=[
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
        self.assertNotIn('\n  web_search', output)
        self.assertIn('\n  read_file', output)

    def test_tool_ask_prompt_declined(self):
        self.chat.config.set('tool_permission', {'web': 'ask'})
        with patch('replio.ui.input', return_value='n'):
            output = self._dispatch('/tool web_search {"query": "x"}')
        self.assertIn('[cancelled]', output)

    def test_tool_ask_prompt_accepted(self):
        self.chat.config.set('tool_permission', {'web': 'ask'})
        with patch.object(self._search_service(), 'search', return_value=[
            {'title': 'T', 'url': 'http://x.com', 'snippet': 'S'}
        ]), patch('replio.ui.input', return_value='y'):
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


class TestConnectCommand(unittest.TestCase):

    def setUp(self):
        self.chat = make_chat()

    def tearDown(self):
        self.chat._tmp.cleanup()

    def _dispatch(self, inputs):
        out = io.StringIO()
        with patch('sys.stdout', new=out):
            with patch('replio.commands.builtins.input', side_effect=inputs):
                self.chat.registry.dispatch('/connect')
        return out.getvalue()

    def test_connect_saves_on_success(self):
        with patch.object(self.chat, 'check_connection',
                          return_value=(True, '3 models available')):
            output = self._dispatch(['', '', 'sk-123', ''])
        self.assertIn('Connected to ollama (https://test.api.com)', output)
        self.assertIn('- 3 models available', output)
        self.assertEqual(self.chat.config.get('base_url'), 'https://test.api.com')
        self.assertEqual(self.chat.config.get('api_key'), 'sk-123')
        self.assertEqual(self.chat.config.get('model'), 'test-model')

    def test_connect_failure_declined_leaves_config(self):
        with patch.object(self.chat, 'check_connection',
                          return_value=(False, 'HTTP 401: bad key')):
            output = self._dispatch(['', '', 'sk-bad', '', 'n'])
        self.assertIn('[Error] Connection test failed: HTTP 401: bad key', output)
        self.assertIn('Connection not saved', output)
        self.assertEqual(self.chat.config.get('api_key'), '')
        self.assertEqual(self.chat.config.get('base_url'), 'https://test.api.com')

    def test_connect_failure_accepted_saves(self):
        with patch.object(self.chat, 'check_connection',
                          return_value=(False, 'HTTP 500: boom')):
            output = self._dispatch(['', '', 'sk-risk', '', 'y'])
        self.assertIn('Connected to ollama (https://test.api.com)', output)
        self.assertEqual(self.chat.config.get('api_key'), 'sk-risk')

    def test_connect_check_disabled_skips_probe(self):
        self.chat.config.set('connect_check', False)
        with patch.object(self.chat, 'check_connection') as probe:
            output = self._dispatch(['', '', 'sk-123', ''])
        probe.assert_not_called()
        self.assertIn('Connected to ollama (https://test.api.com)', output)
        self.assertNotIn('models available', output)
        self.assertEqual(self.chat.config.get('api_key'), 'sk-123')

    def test_connect_passes_probe_entered_values(self):
        with patch.object(self.chat, 'check_connection',
                          return_value=(True, 'ok')) as probe:
            self._dispatch(['my-provider', 'https://x.example/v1', 'sk-x', 'm1'])
        probe.assert_called_once_with(
            base_url='https://x.example/v1', api_key='sk-x',
            model='m1', provider='my-provider')

    def test_connect_detects_provider_before_probe(self):
        with patch.object(self.chat, 'check_connection',
                          return_value=(True, 'ok')) as probe:
            output = self._dispatch(['ollama', 'https://api.groq.com/openai/v1', '', ''])
        probe.assert_called_once_with(
            base_url='https://api.groq.com/openai/v1', api_key='',
            model='test-model', provider='groq')
        self.assertIn('Detected provider "groq"', output)


class TestProviderWarn(unittest.TestCase):

    def setUp(self):
        self.chat = make_chat()

    def tearDown(self):
        self.chat._tmp.cleanup()

    def _dispatch(self, line):
        out = io.StringIO()
        with patch('sys.stdout', new=out):
            self.chat.registry.dispatch(line)
        return out.getvalue()

    def test_provider_failed_probe_warns(self):
        with patch.object(self.chat, 'check_connection',
                          return_value=(False, 'HTTP 500: boom')):
            output = self._dispatch('/provider openai')
        self.assertIn('Provider set to: openai', output)
        self.assertIn('Warning: connection test failed - HTTP 500: boom', output)
        self.assertIn('Run /connect', output)

    def test_provider_success_no_warning(self):
        with patch.object(self.chat, 'check_connection',
                          return_value=(True, 'ok')):
            output = self._dispatch('/provider openai')
        self.assertIn('Provider set to: openai', output)
        self.assertNotIn('Warning', output)

    def test_provider_no_probe_when_disabled(self):
        self.chat.config.set('connect_check', False)
        with patch.object(self.chat, 'check_connection') as probe:
            output = self._dispatch('/provider openai')
        probe.assert_not_called()
        self.assertNotIn('Warning', output)


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
        with self._buffer('se'):
            self.assertIsNone(self.chat._completer('se', 0))

    def test_command_completion_outside_session_context(self):
        with self._buffer('/session'):
            self.assertEqual(self.chat._completer('/session', 0), '/session ')


class TestThinkingCommand(unittest.TestCase):

    def setUp(self):
        self.chat = make_chat()

    def tearDown(self):
        self.chat._tmp.cleanup()

    def _dispatch(self, line):
        out = io.StringIO()
        with patch('sys.stdout', new=out):
            self.chat.registry.dispatch(line)
        return out.getvalue()

    def test_thinking_reports_current_state(self):
        output = self._dispatch('/thinking')
        self.assertIn('Thinking streaming: off', output)

    def test_thinking_off(self):
        output = self._dispatch('/thinking off')
        self.assertIn('Thinking streaming: off', output)
        self.assertIs(self.chat.config.get('show_thinking'), False)

    def test_thinking_on(self):
        output = self._dispatch('/thinking on')
        self.assertIn('Thinking streaming: on', output)
        self.assertIs(self.chat.config.get('show_thinking'), True)

    def test_thinking_status_no_change(self):
        self._dispatch('/thinking on')
        output = self._dispatch('/thinking status')
        self.assertIn('Thinking streaming: on', output)
        self.assertIs(self.chat.config.get('show_thinking'), True)

    def test_thinking_invalid_arg(self):
        self._dispatch('/thinking on')
        output = self._dispatch('/thinking bogus')
        self.assertIn('Usage: /thinking', output)
        self.assertIs(self.chat.config.get('show_thinking'), True)


class TestModeCommand(unittest.TestCase):

    def setUp(self):
        self.chat = make_chat()

    def tearDown(self):
        self.chat._tmp.cleanup()

    def _dispatch(self, line):
        out = io.StringIO()
        with patch('sys.stdout', new=out):
            self.chat.registry.dispatch(line)
        return out.getvalue()

    def test_mode_shows_current_and_list(self):
        output = self._dispatch('/mode')
        self.assertIn('Current mode: build', output)
        self.assertIn('plan', output)
        self.assertIn('build  <-- current', output)

    def test_mode_switch(self):
        output = self._dispatch('/mode plan')
        self.assertIn('Mode set to: plan', output)
        self.assertEqual(self.chat.config.get('mode'), 'plan')

    def test_mode_unknown(self):
        output = self._dispatch('/mode nosuch')
        self.assertIn('Unknown mode "nosuch"', output)
        self.assertIn('build', output)
        self.assertEqual(self.chat.config.get('mode'), 'build')

    def test_plan_mode_denies_write_tool(self):
        self._dispatch('/mode plan')
        output = self._dispatch('/tool write_file {"path": "x.txt", "content": "x"}')
        self.assertIn('disabled by tool policy', output)

    def test_plan_mode_filters_schema(self):
        self._dispatch('/mode plan')
        schema = self.chat._init_tooling()
        names = [s['function']['name'] for s in schema]
        self.assertNotIn('write_file', names)
        self.assertNotIn('run_command', names)
        self.assertIn('read_file', names)

    def test_plan_mode_tool_listing_hides_write_tools(self):
        self._dispatch('/mode plan')
        output = self._dispatch('/tool')
        self.assertNotIn('\n  write_file', output)
        self.assertNotIn('\n  run_command', output)
        self.assertIn('\n  read_file', output)

    def test_plan_mode_help_lists_hides_write_tools(self):
        self._dispatch('/mode plan')
        output = self._dispatch('/help')
        self.assertNotIn('\n    write_file', output)
        self.assertNotIn('\n    run_command', output)
        self.assertIn('\n    read_file', output)
        self.assertIn('\n    list_dir', output)

    def test_switch_back_to_build_restores_tools(self):
        self._dispatch('/mode plan')
        self._dispatch('/mode build')
        schema = self.chat._init_tooling()
        names = [s['function']['name'] for s in schema]
        self.assertIn('write_file', names)
        self.assertIn('run_command', names)


class TestModeCompleter(unittest.TestCase):

    def setUp(self):
        self.chat = make_chat()

    def tearDown(self):
        self.chat._tmp.cleanup()

    def test_mode_completes_names(self):
        with patch('replio.chat.readline.get_line_buffer', return_value='/mode b'):
            self.assertEqual(self.chat._completer('b', 0), 'build ')
            self.assertIsNone(self.chat._completer('b', 1))
        with patch('replio.chat.readline.get_line_buffer', return_value='/mode '):
            matches = []
            i = 0
            while True:
                m = self.chat._completer('', i)
                if m is None:
                    break
                matches.append(m)
                i += 1
        self.assertEqual(matches, ['build ', 'plan '])


if __name__ == '__main__':
    unittest.main()
