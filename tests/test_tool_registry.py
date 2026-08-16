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
        self.assertEqual(names, ['run_command', 'read_file', 'list_dir',
                                 'write_file', 'glob', 'grep',
                                 'web_search', 'fetch_page'])

    def test_execute_drops_undeclared_and_none_args(self):
        out = self.registry.execute('list_dir',
                                    {'path': '.', 'depth': None, 'bogus': 1})
        self.assertNotIn('Error', out)

    def test_execute_unknown_tool(self):
        out = self.registry.execute('nonexistent', {})
        self.assertIn('unknown tool', out)

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
