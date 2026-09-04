import tempfile
import unittest
from pathlib import Path

from replio.providers.registry import ProviderRegistry
from replio.config import Config


class TestProviderRegistry(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _reg(self):
        return ProviderRegistry(global_dir=self.base)

    def test_path_under_global_dir(self):
        self.assertEqual(self._reg().path,
                         self.base / '.config' / 'replio' / 'providers.json')

    def test_put_and_find(self):
        reg = self._reg()
        reg.put('ollama', 'https://api.ollama.com', 'key-1')
        entry = reg.find('ollama')
        self.assertIsNotNone(entry)
        self.assertEqual(entry.provider, 'ollama')
        self.assertEqual(entry.base_url, 'https://api.ollama.com')
        self.assertEqual(entry.api_key, 'key-1')
        self.assertTrue(entry.added_at)
        self.assertTrue(entry.last_used)

    def test_put_dedupes_by_provider_and_updates_key(self):
        reg = self._reg()
        reg.put('ollama', 'u', 'k1')
        reg.put('ollama', 'u', 'k2')
        self.assertEqual(len(reg.all()), 1)
        self.assertEqual(reg.find('ollama').api_key, 'k2')

    def test_put_empty_key_keeps_existing(self):
        reg = self._reg()
        reg.put('ollama', 'u', 'keep')
        reg.put('ollama', 'u', '')
        self.assertEqual(reg.find('ollama').api_key, 'keep')

    def test_put_missing_base_url_keeps_custom(self):
        reg = self._reg()
        reg.put('ollama', 'https://custom.example/v1', 'k')
        reg.put('ollama', api_key='k2')
        self.assertEqual(reg.find('ollama').base_url, 'https://custom.example/v1')
        self.assertEqual(reg.find('ollama').api_key, 'k2')

    def test_api_key_for(self):
        reg = self._reg()
        reg.put('ollama', 'u', 'k')
        self.assertEqual(reg.api_key_for('ollama'), 'k')
        self.assertEqual(reg.api_key_for('openai'), '')

    def test_base_url_for_falls_back_to_default(self):
        reg = self._reg()
        self.assertEqual(reg.base_url_for('ollama', 'https://api.ollama.com'),
                         'https://api.ollama.com')
        reg.put('ollama', 'https://custom.example/v1', 'k')
        self.assertEqual(reg.base_url_for('ollama', 'https://api.ollama.com'),
                         'https://custom.example/v1')

    def test_touch_updates_last_used(self):
        reg = self._reg()
        reg.put('ollama', 'u', 'k')
        before = reg.find('ollama').last_used
        reg.touch('ollama')
        self.assertGreaterEqual(reg.find('ollama').last_used, before)

    def test_touch_unknown_returns_none(self):
        self.assertIsNone(self._reg().touch('nope'))

    def test_file_0600_when_keyed(self):
        reg = self._reg()
        reg.put('ollama', 'u', 'secret')
        self.assertEqual(reg.path.stat().st_mode & 0o777, 0o600)

    def test_reload_from_disk(self):
        self._reg().put('ollama', 'u', 'k')
        reg2 = ProviderRegistry(global_dir=self.base)
        self.assertEqual(reg2.find('ollama').api_key, 'k')

    def test_corrupt_file_tolerated(self):
        reg = self._reg()
        reg.put('ollama', 'u', 'k')
        self.base.joinpath('.config', 'replio').mkdir(parents=True, exist_ok=True)
        self.base.joinpath('.config', 'replio', 'providers.json').write_text('{oops')
        reg2 = ProviderRegistry(global_dir=self.base)
        self.assertEqual(reg2.all(), [])

    def test_remove(self):
        reg = self._reg()
        reg.put('ollama', 'u', 'k')
        self.assertTrue(reg.remove('ollama'))
        self.assertIsNone(reg.find('ollama'))
        self.assertFalse(reg.remove('ollama'))

    def test_default_uses_config_global_dir(self):
        prev = Config.GLOBAL_DIR
        Config.GLOBAL_DIR = self.base
        try:
            reg = ProviderRegistry()
            self.assertEqual(reg.path,
                             self.base / '.config' / 'replio' / 'providers.json')
        finally:
            Config.GLOBAL_DIR = prev


if __name__ == '__main__':
    unittest.main()