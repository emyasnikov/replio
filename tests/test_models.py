import tempfile
import unittest
from pathlib import Path

from replio.models import ModelRegistry
from replio.config import Config


class TestModelRegistry(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _reg(self):
        return ModelRegistry(global_dir=self.base)

    def test_path_under_global_dir(self):
        self.assertEqual(self._reg().path,
                         self.base / '.config' / 'replio' / 'models.json')

    def test_put_and_find(self):
        reg = self._reg()
        reg.put('ollama', 'https://api.ollama.com', 'm1', 'key-1')
        entry = reg.find('ollama', 'https://api.ollama.com', 'm1')
        self.assertIsNotNone(entry)
        self.assertEqual(entry.api_key, 'key-1')
        self.assertTrue(entry.added_at)
        self.assertTrue(entry.last_used)

    def test_put_dedupes_and_updates_key(self):
        reg = self._reg()
        reg.put('ollama', 'u', 'm', 'k1')
        reg.put('ollama', 'u', 'm', 'k2')
        self.assertEqual(len(reg.all()), 1)
        self.assertEqual(reg.find('ollama', 'u', 'm').api_key, 'k2')

    def test_put_custom_provider(self):
        reg = self._reg()
        reg.put('openai', 'https://api.openai.com/v1', 'gpt-4o', 'oak')
        entry = reg.find('openai', 'https://api.openai.com/v1', 'gpt-4o')
        self.assertEqual(entry.api_key, 'oak')

    def test_put_empty_key_keeps_existing(self):
        reg = self._reg()
        reg.put('ollama', 'u', 'm2', 'keep')
        reg.put('ollama', 'u', 'm2', '')
        self.assertEqual(reg.find('ollama', 'u', 'm2').api_key, 'keep')

    def test_touch_reorders_by_last_used(self):
        reg = self._reg()
        reg.put('ollama', 'u', 'a')
        reg.put('ollama', 'u', 'b')
        reg.touch('ollama', 'u', 'a')
        self.assertEqual(reg.all()[0].model, 'a')
        self.assertEqual(reg.all()[1].model, 'b')

    def test_touch_unknown_returns_none(self):
        self.assertIsNone(self._reg().touch('ollama', 'u', 'nope'))

    def test_api_key_for(self):
        reg = self._reg()
        reg.put('ollama', 'u', 'm', 'k')
        self.assertEqual(reg.api_key_for('ollama', 'u', 'm'), 'k')
        self.assertEqual(reg.api_key_for('ollama', 'u', 'nope'), '')

    def test_grouped(self):
        reg = self._reg()
        reg.put('ollama', 'https://a', 'm1')
        reg.put('ollama', 'https://a', 'm2')
        reg.put('openai', 'https://b', 'g1')
        groups = dict(reg.grouped())
        self.assertEqual(len(groups['ollama (https://a)']), 2)
        self.assertEqual(len(groups['openai (https://b)']), 1)

    def test_file_0600_when_keyed(self):
        reg = self._reg()
        reg.put('ollama', 'u', 'm', 'secret')
        self.assertEqual(reg.path.stat().st_mode & 0o777, 0o600)

    def test_reload_from_disk(self):
        self._reg().put('ollama', 'u', 'm', 'k')
        reg2 = ModelRegistry(global_dir=self.base)
        self.assertEqual(reg2.find('ollama', 'u', 'm').api_key, 'k')

    def test_remove(self):
        reg = self._reg()
        reg.put('ollama', 'u', 'm')
        self.assertTrue(reg.remove('ollama', 'u', 'm'))
        self.assertIsNone(reg.find('ollama', 'u', 'm'))
        self.assertFalse(reg.remove('ollama', 'u', 'm'))

    def test_default_uses_config_global_dir(self):
        prev = Config.GLOBAL_DIR
        Config.GLOBAL_DIR = self.base
        try:
            reg = ModelRegistry()
            self.assertEqual(reg.path,
                             self.base / '.config' / 'replio' / 'models.json')
        finally:
            Config.GLOBAL_DIR = prev


if __name__ == '__main__':
    unittest.main()