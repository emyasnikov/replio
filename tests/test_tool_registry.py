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


if __name__ == '__main__':
    unittest.main()
