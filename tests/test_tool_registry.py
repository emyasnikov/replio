import unittest

from replio.tools.registry import ToolRegistry
from replio.tools.builtins import register_tools


class TestToolRegistry(unittest.TestCase):

    def setUp(self):
        self.registry = ToolRegistry()
        register_tools(self.registry)

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
        self.assertEqual(names, ['web_search', 'fetch_page'])

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
