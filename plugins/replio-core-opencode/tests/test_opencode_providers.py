import sys
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from opencode import OpenCodeProvider
from opencode_go import OpenCodeGoProvider


class TestOpenCodeDefaults(unittest.TestCase):

    def test_opencode_defaults(self):
        p = OpenCodeProvider()
        self.assertEqual(p.base_url, 'https://opencode.ai/zen/v1')
        self.assertEqual(p.model, 'kimi-k3')

    def test_opencode_go_defaults(self):
        p = OpenCodeGoProvider()
        self.assertEqual(p.base_url, 'https://opencode.ai/zen/go/v1')
        self.assertEqual(p.model, 'deepseek-v4-flash')

    def test_endpoints(self):
        self.assertEqual(OpenCodeProvider()._endpoint(),
                         'https://opencode.ai/zen/v1/chat/completions')
        self.assertEqual(OpenCodeGoProvider()._endpoint(),
                         'https://opencode.ai/zen/go/v1/chat/completions')

    def test_ref_prefix_stripped(self):
        p = OpenCodeProvider(model='opencode/kimi-k3')
        payload = p._payload([{'role': 'user', 'content': 'hi'}])
        self.assertEqual(payload['model'], 'kimi-k3')
        g = OpenCodeGoProvider(model='opencode-go/deepseek-v4-flash')
        payload = g._payload([{'role': 'user', 'content': 'hi'}])
        self.assertEqual(payload['model'], 'deepseek-v4-flash')

    def test_bare_model_kept(self):
        g = OpenCodeGoProvider(model='deepseek-v4-flash')
        payload = g._payload([{'role': 'user', 'content': 'hi'}])
        self.assertEqual(payload['model'], 'deepseek-v4-flash')


class TestOpenCodeHeaders(unittest.TestCase):

    def _cases(self):
        return (OpenCodeProvider(), OpenCodeGoProvider())

    def test_session_header_present_and_stable(self):
        for p in self._cases():
            first = p._headers()['x-opencode-session']
            second = p._headers()['x-opencode-session']
            self.assertTrue(first)
            self.assertEqual(first, second)

    def test_session_id_override(self):
        p = OpenCodeGoProvider(session_id='my-conversation-1')
        self.assertEqual(p._headers()['x-opencode-session'], 'my-conversation-1')

    def test_identifying_user_agent(self):
        for p in self._cases():
            self.assertTrue(p._headers()['User-Agent'].startswith('replio/'))


if __name__ == '__main__':
    unittest.main()