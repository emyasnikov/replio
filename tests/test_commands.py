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


if __name__ == '__main__':
    unittest.main()
