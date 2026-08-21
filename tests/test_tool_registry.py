import tempfile
import unittest
from pathlib import Path

from replio.config import Config
from replio.plugins.manager import PluginManager
from replio.tools.registry import ToolRegistry


class TestToolRegistry(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.pm = PluginManager(Config(path=self._tmp.name))
        self.pm.load()
        self.registry = ToolRegistry()
        self.pm.register_tools(self.registry)

    def tearDown(self):
        self._tmp.cleanup()

    def test_web_search_requires_refine(self):
        self.assertTrue(self.registry.refine_required('web_search'))

    def test_fetch_page_no_refine(self):
        self.assertFalse(self.registry.refine_required('fetch_page'))

    def test_unknown_tool_no_refine(self):
        self.assertFalse(self.registry.refine_required('nonexistent'))

    def test_names(self):
        self.assertIn('web_search', self.registry.names())
        self.assertIn('fetch_page', self.registry.names())

    def test_schema(self):
        names = [s['function']['name'] for s in self.registry.schema()]
        self.assertEqual(names, [
            'run_command', 'bash', 'exec',
            'read_file', 'read', 'view', 'list_dir', 'ls', 'write_file',
            'glob', 'grep',
            'mcp_connect', 'mcp_list', 'mcp_disconnect',
            'web_search', 'fetch_page', 'open',
        ])

    def test_execute_drops_undeclared_and_none_args(self):
        out = self.registry.execute('list_dir',
                                    {'path': '.', 'depth': None, 'bogus': 1})
        self.assertNotIn('Error', out)

    def test_execute_unknown_tool(self):
        out = self.registry.execute('nonexistent', {})
        self.assertIn('unknown tool', out)

    def test_execute_passes_config_to_declared_handler(self):
        reg = ToolRegistry()
        params = {'type': 'object', 'properties': {}, 'required': []}
        seen = {}

        @reg.register('peek_cfg', 'Peek', params)
        def peek_cfg(_config=None):
            seen['config'] = _config
            return 'ok'

        class FakeConfig:
            def get(self, key, default=None):
                return default

        out = reg.execute('peek_cfg', {}, config=FakeConfig())
        self.assertEqual(out, 'ok')
        self.assertIsNotNone(seen['config'])

    def test_execute_ignores_config_for_plain_handler(self):
        reg = ToolRegistry()
        params = {'type': 'object', 'properties': {}, 'required': []}

        @reg.register('plain', 'Plain', params)
        def plain():
            return 'ok'

        out = reg.execute('plain', {}, config=object())
        self.assertEqual(out, 'ok')

    def test_custom_refine_metadata(self):
        reg = ToolRegistry()

        @reg.register('do_stuff', 'Do something', {}, refine=True)
        def do_stuff():
            return 'ok'

        self.assertTrue(reg.refine_required('do_stuff'))

    def test_permission_metadata(self):
        self.assertEqual(self.registry.permission_for('web_search'), 'web')
        self.assertEqual(self.registry.permission_for('fetch_page'), 'read')
        self.assertEqual(self.registry.key_arg_for('web_search'), 'query')
        self.assertEqual(self.registry.path_arg_for('fetch_page'), None)

    def test_schema_filtered(self):
        schema = self.registry.schema_filtered({'web_search'})
        names = [s['function']['name'] for s in schema]
        self.assertEqual(names, ['web_search'])

    def test_status_parts_uses_key_arg_value(self):
        value, body = self.registry.status_parts(
            'web_search', {'query': 'latest python', 'junk': 1})
        self.assertEqual(value, 'latest python')
        self.assertEqual(body, [])

    def test_status_parts_truncates_long_value(self):
        value, body = self.registry.status_parts('run_command', {'command': 'x' * 200})
        self.assertEqual(len(value), 80)
        self.assertEqual(body, [])

    def test_status_parts_unknown_tool(self):
        value, body = self.registry.status_parts('nonexistent', {})
        self.assertEqual(value, 'nonexistent')
        self.assertEqual(body, [])

    def test_write_file_new_file_preview(self):
        path = str(Path(self._tmp.name) / 'new.md')
        value, body = self.registry.status_parts(
            'write_file', {'path': path, 'content': 'First line\nSecond line\n'})
        self.assertEqual(value, path)
        self.assertEqual(body[:2], ['+ First line', '+ Second line'])
        self.assertEqual(body[-1], f'({Path(path).resolve()} - 2 lines, 23 chars, created)')

    def test_write_file_existing_file_diff(self):
        p = Path(self._tmp.name) / 'edit.md'
        p.write_text('old line\n')
        value, body = self.registry.status_parts(
            'write_file', {'path': str(p), 'content': 'new line\n'})
        self.assertEqual(value, str(p))
        self.assertIn('-old line', body)
        self.assertIn('+new line', body)
        self.assertEqual(body[-1], f'({p.resolve()} - 1 lines, 9 chars, overwritten)')

    def test_write_file_append_summary(self):
        p = Path(self._tmp.name) / 'append.md'
        p.write_text('a\n')
        value, body = self.registry.status_parts(
            'write_file', {'path': str(p), 'content': 'b\n', 'mode': 'a'})
        self.assertEqual(body[-1], f'({p.resolve()} - 1 lines, 2 chars, appended)')

    def test_echo_metadata(self):
        self.assertTrue(self.registry.echo_for('run_command'))
        self.assertFalse(self.registry.echo_for('write_file'))
        self.assertFalse(self.registry.echo_for('nonexistent'))

    def test_activity_category_defaults(self):
        self.assertEqual(self.registry.activity('web_search', {'query': 'hi there'}),
                         ('%', 'Search', 'hi there', ''))
        self.assertEqual(self.registry.activity('run_command', {'command': 'echo hi'}),
                         ('$', 'Run', 'echo hi', ''))
        self.assertEqual(self.registry.activity('write_file', {'path': 'a.md', 'content': 'x'}),
                         ('→', 'Write', 'a.md', 'content=x'))
        self.assertEqual(self.registry.activity('read_file', {'path': 'a.py'}),
                         ('←', 'Read', 'a.py', ''))

    def test_activity_params_exclude_key_arg_in_schema_order(self):
        self.assertEqual(
            self.registry.activity('open', {'url': 'https://example.com', 'offset': 0}),
            ('↓', 'Open', 'https://example.com', 'offset=0'))
        self.assertEqual(
            self.registry.activity('run_command',
                                   {'command': 'ls', 'cwd': '/workspace', 'timeout': 10000}),
            ('$', 'Run', 'ls', 'cwd=/workspace, timeout=10000'))

    def test_activity_params_aliases_resolved(self):
        self.assertEqual(
            self.registry.activity('read_file', {'file': 'a.py', 'limit': 5}),
            ('←', 'Read', 'a.py', 'limit=5'))

    def test_activity_per_tool_override(self):
        self.assertEqual(self.registry.activity('glob', {'pattern': '**/*.py'}),
                         ('*', 'Glob', '**/*.py', ''))
        self.assertEqual(self.registry.activity('fetch_page', {'url': 'https://x.dev/p'}),
                         ('↓', 'Fetch', 'https://x.dev/p', ''))

    def test_activity_fs_list_and_grep_glyphs(self):
        self.assertEqual(self.registry.activity('list_dir', {'path': 'x', 'depth': 2}),
                         ('*', 'List', 'x', 'depth=2'))
        self.assertEqual(self.registry.activity('grep', {'pattern': 'foo', 'path': 'src'}),
                         ('*', 'Grep', 'foo', 'path=src'))

    def test_activity_truncates_long_value(self):
        glyph, verb, label, params = self.registry.activity('run_command', {'command': 'x' * 200})
        self.assertEqual((glyph, verb), ('$', 'Run'))
        self.assertEqual(len(label), 80)
        self.assertEqual(params, '')

    def test_activity_missing_key_arg_falls_back_to_name(self):
        self.assertEqual(self.registry.activity('run_command', {}),
                         ('$', 'Run', 'run_command', ''))

    def test_activity_unknown_tool(self):
        self.assertIsNone(self.registry.activity('nonexistent', {}))

    def test_activity_unmapped_category(self):
        reg = ToolRegistry()
        params = {'type': 'object', 'properties': {}, 'required': []}

        @reg.register('do_stuff', 'Do something', params, category='custom')
        def do_stuff():
            return 'ok'

        self.assertIsNone(reg.activity('do_stuff', {}))

    def test_activity_partial_override_keeps_category_default(self):
        reg = ToolRegistry()
        params = {'type': 'object',
                  'properties': {'path': {'type': 'string'}},
                  'required': ['path']}

        @reg.register('peek_dir', 'Peek', params, category='read', key_arg='path',
                      verb='Scan')
        def peek_dir(path):
            return 'ok'

        self.assertEqual(reg.activity('peek_dir', {'path': '/x'}),
                         ('←', 'Scan', '/x', ''))

    def test_custom_status_callback(self):
        reg = ToolRegistry()
        params = {
            'type': 'object',
            'properties': {'path': {'type': 'string'},
                           'content': {'type': 'string'}},
            'required': ['path', 'content'],
        }

        @reg.register('do_stuff', 'Do', params, key_arg='path',
                      status=lambda args: f"{args['path']}\n+ {args['content']}")
        def do_stuff(path, content):
            return 'ok'

        value, body = reg.status_parts('do_stuff', {'path': 'p', 'content': 'c'})
        self.assertEqual(value, 'p')
        self.assertEqual(body, ['+ c'])


if __name__ == '__main__':
    unittest.main()
