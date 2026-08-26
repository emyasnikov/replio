import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from replio.config import Config, DEFAULT_CONFIG
from replio.cli import cmd_config


class _IsolatedConfigBase(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / 'home'
        self.home.mkdir()
        self._prev_global_dir = Config.GLOBAL_DIR
        Config.GLOBAL_DIR = self.home
        self.project = Path(self.tmp.name) / 'project'
        (self.project / '.replio').mkdir(parents=True)

    def tearDown(self):
        Config.GLOBAL_DIR = self._prev_global_dir
        self.tmp.cleanup()

    @property
    def local_path(self):
        return self.project / '.replio' / 'config.json'

    @property
    def global_path(self):
        return self.home / '.config' / 'replio' / 'config.json'

    def local(self):
        if not self.local_path.exists():
            return {}
        return json.loads(self.local_path.read_text())

    def global_(self):
        if not self.global_path.exists():
            return {}
        return json.loads(self.global_path.read_text())


class TestConfigScopes(_IsolatedConfigBase):

    def test_set_default_writes_local_only(self):
        c = Config(path=str(self.project))
        c.set('temperature', 0.3)
        self.assertEqual(self.local(), {'temperature': 0.3})
        self.assertFalse(self.global_path.exists())
        self.assertEqual(c.get('temperature'), 0.3)

    def test_set_global_writes_global_not_local(self):
        c = Config(path=str(self.project))
        c.set('max_tokens', 0, scope='global')
        self.assertEqual(self.global_(), {'max_tokens': 0})
        self.assertFalse(self.local_path.exists())
        self.assertEqual(c.get('max_tokens'), 0)

    def test_local_holds_only_local_selection(self):
        c = Config(path=str(self.project))
        c.set('max_tokens', 0, scope='global')
        c.set('model', 'local-model')
        self.assertEqual(self.local(), {'model': 'local-model'})

    def test_set_global_does_not_shadow_local(self):
        c = Config(path=str(self.project))
        c.set('model', 'local-model')
        c.set('model', 'global-model', scope='global')
        self.assertEqual(c.get('model'), 'local-model')
        self.assertEqual(self.global_()['model'], 'global-model')
        self.assertEqual(self.local()['model'], 'local-model')

    def test_set_global_empty_local_value_does_not_shadow(self):
        c = Config(path=str(self.project))
        c.set('max_tokens', '', scope='local')
        c.set('max_tokens', 4096, scope='global')
        self.assertEqual(c.get('max_tokens'), 4096)

    def test_unset_restores_global_fallback(self):
        c = Config(path=str(self.project))
        c.set('model', 'local-model')
        c.set('model', 'global-model', scope='global')
        c.unset('model')
        self.assertNotIn('model', self.local())
        self.assertEqual(c.get('model'), 'global-model')

    def test_unset_restores_default(self):
        c = Config(path=str(self.project))
        c.set('max_tokens', 2048)
        c.unset('max_tokens')
        self.assertEqual(c.get('max_tokens'), DEFAULT_CONFIG['max_tokens'])
        self.assertNotIn('max_tokens', self.local())

    def test_unset_global_keeps_local(self):
        c = Config(path=str(self.project))
        c.set('model', 'local-model')
        c.set('model', 'global-model', scope='global')
        c.unset('model', scope='global')
        self.assertEqual(c.get('model'), 'local-model')

    def test_apply_is_in_memory_only(self):
        c = Config(path=str(self.project))
        c.apply('temperature', 0.5)
        self.assertEqual(c.get('temperature'), 0.5)
        self.assertFalse(self.local_path.exists())
        self.assertFalse(self.global_path.exists())

    def test_apply_does_not_survive_reload(self):
        c = Config(path=str(self.project))
        c.apply('temperature', 0.5)
        c2 = Config(path=str(self.project))
        self.assertEqual(c2.get('temperature'),
                         DEFAULT_CONFIG['temperature'])

    def test_origin(self):
        c = Config(path=str(self.project))
        self.assertEqual(c.origin('temperature'), 'default')
        c.set('model', 'global-model', scope='global')
        self.assertEqual(c.origin('model'), 'global')
        c.set('model', 'local-model')
        self.assertEqual(c.origin('model'), 'local')

    def test_load_merges_global_then_local(self):
        c = Config(path=str(self.project))
        c.set('temperature', 0.2, scope='global')
        c.set('temperature', 0.9)
        c2 = Config(path=str(self.project))
        self.assertEqual(c2.get('temperature'), 0.9)


class TestConfigCli(_IsolatedConfigBase):

    def _args(self, **kw):
        base = dict(path=str(self.project), global_=False, action=None,
                    key=None, value=None, show_origin=False)
        base.update(kw)
        return SimpleNamespace(**base)

    def _run(self, args):
        out = io.StringIO()
        with patch('sys.stdout', new=out):
            rc = cmd_config(args)
        return rc, out.getvalue()

    def test_get_single_key(self):
        c = Config(path=str(self.project))
        c.set('temperature', 0.3)
        rc, out = self._run(self._args(action='get', key='temperature'))
        self.assertEqual(rc, 0)
        self.assertIn('temperature = 0.3', out)

    def test_get_show_origin(self):
        c = Config(path=str(self.project))
        c.set('model', 'local-model')
        rc, out = self._run(self._args(action='get', key='model',
                                       show_origin=True))
        self.assertIn('(local)', out)

    def test_set_local(self):
        rc, out = self._run(self._args(
            action='set', key='temperature', value='0.3'))
        self.assertEqual(rc, 0)
        self.assertEqual(self.local()['temperature'], 0.3)
        self.assertIn('saved to local config', out)

    def test_set_global(self):
        rc, _ = self._run(self._args(
            action='set', key='max_tokens', value='0', global_=True))
        self.assertEqual(rc, 0)
        self.assertEqual(self.global_()['max_tokens'], 0)
        self.assertEqual(self.local(), {})

    def test_set_json_value(self):
        rc, _ = self._run(self._args(
            action='set', key='tools.deny', value='["run_command"]'))
        self.assertEqual(rc, 0)
        self.assertEqual(self.local()['tools.deny'], ['run_command'])

    def test_set_requires_value(self):
        rc, _ = self._run(self._args(action='set', key='temperature'))
        self.assertEqual(rc, 1)
        self.assertFalse(self.local_path.exists())

    def test_set_api_key_is_a_normal_key(self):
        rc, _ = self._run(self._args(action='set', key='api_key',
                                     value='cli-secret'))
        self.assertEqual(rc, 0)
        self.assertEqual(self.local()['api_key'], 'cli-secret')
        self.assertNotIn('api_key', self.global_())

    def test_unset_local(self):
        Config(path=str(self.project)).set('max_tokens', 2048)
        rc, _ = self._run(self._args(action='unset', key='max_tokens'))
        self.assertEqual(rc, 0)
        self.assertNotIn('max_tokens', self.local())
        fresh = Config(path=str(self.project))
        self.assertEqual(fresh.get('max_tokens'),
                         DEFAULT_CONFIG['max_tokens'])


if __name__ == '__main__':
    unittest.main()