import tempfile
import unittest

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

    def test_execute_drops_undeclared_args(self):
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


if __name__ == '__main__':
    unittest.main()
