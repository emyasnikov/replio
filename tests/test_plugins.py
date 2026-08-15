import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from replio.config import Config
from replio.plugins.manager import PluginManager, PluginError, version_matches
from replio.tools.registry import ToolRegistry
from replio.tools.policy import ToolPolicy
from replio.commands.registry import CommandRegistry
from replio.ui import NullUI


SIMPLE_TOOL_PLUGIN = '''
def register_tools(registry):
    @registry.register(
        name='hello',
        description='Say hello',
        parameters={'type': 'object', 'properties': {}},
    )
    def hello():
        return 'hello from plugin'
'''

PROVIDER_PLUGIN = '''
from replio.providers.base import OpenAICompatibleProvider


class MyProvider(OpenAICompatibleProvider):
    DEFAULT_BASE_URL = 'https://my.example.com'
    DEFAULT_MODEL = 'my-model'


def register_providers(providers):
    providers['myprovider'] = MyProvider
'''

COMMAND_PLUGIN = '''
def register_commands(commands):
    @commands.register('frobnicate', description='Frobnicate')
    def frob(_=None):
        print('frobbed')
'''

LAZY_DEP_PLUGIN = '''
def register_tools(registry):
    @registry.register(
        name='uses_dep',
        description='Use a missing dependency',
        parameters={'type': 'object', 'properties': {}},
    )
    def uses_dep():
        try:
            import replio_definitely_missing_pkg
        except ImportError:
            return 'Error: uses_dep requires "replio_definitely_missing_pkg" — pip install replio_definitely_missing_pkg'
        return 'ok'
'''

POLICY_PLUGIN = '''
def register_tools(registry):
    @registry.register(
        name='confidential',
        description='Read a secret file',
        parameters={'type': 'object', 'properties': {}},
        category='read',
        permission='read',
    )
    def confidential():
        return 'secret'
'''

SERVICE_PLUGIN = '''
def register_services(services):
    services['greet'] = lambda: 'hello from service'
'''


SIMPLE_MANIFEST = {
    'name': 'hello',
    'version': '1.2.3',
    'description': 'A test plugin',
    'provides': {'tools': ['hello'], 'providers': [], 'commands': []},
}


def write_plugin(plugins_root, name, entry, manifest=None):
    pdir = plugins_root / name
    pdir.mkdir(parents=True, exist_ok=True)
    if manifest is not None:
        with open(pdir / 'manifest.json', 'w') as f:
            json.dump(manifest, f)
    with open(pdir / 'plugin.py', 'w') as f:
        f.write(entry)


def write_bare_py(plugins_root, name, content):
    (plugins_root / f'{name}.py').write_text(content)


class TestVersionMatches(unittest.TestCase):

    def test_empty_constraint(self):
        self.assertTrue(version_matches('0.13.0', ''))

    def test_operator_ranges(self):
        self.assertTrue(version_matches('0.13.0', '>=0.12.0,<1.0'))
        self.assertTrue(version_matches('0.12.0', '==0.12.0'))
        self.assertTrue(version_matches('0.12.5', '>=0.12.0,<0.13.0'))

    def test_operator_ranges_reject(self):
        self.assertFalse(version_matches('0.11.0', '>=0.12.0'))
        self.assertFalse(version_matches('1.1.0', '<1.0'))
        self.assertFalse(version_matches('0.13.0', '<=0.12.0'))
        self.assertFalse(version_matches('0.12.5', '==0.12.0'))


class PluginTestBase(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.plugins_dir = self.root / '.replio' / 'plugins'
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        with open(self.root / '.replio' / 'config.json', 'w') as f:
            json.dump({'plugins': []}, f)
        self.config = Config(path=self.root)
        self.pm = PluginManager(self.config)

    def tearDown(self):
        self.tmp.cleanup()

    def make_pm(self, config_data=None):
        data = {'plugins': []}
        if config_data:
            data.update(config_data)
        with open(self.root / '.replio' / 'config.json', 'w') as f:
            json.dump(data, f)
        self.config = Config(path=self.root)
        return PluginManager(self.config)


class TestDiscovery(PluginTestBase):

    def test_bare_py_plugin(self):
        write_bare_py(self.plugins_dir, 'hello', SIMPLE_TOOL_PLUGIN)
        self.pm.load()
        info = self.pm.get('hello')
        self.assertIsNotNone(info)
        self.assertEqual(info.entry, 'hello.py')
        self.assertEqual(info.version, '0.0.0')
        self.assertEqual(info.status, 'loaded')

    def test_directory_plugin_manifest(self):
        write_plugin(self.plugins_dir, 'hello', SIMPLE_TOOL_PLUGIN, SIMPLE_MANIFEST)
        self.pm.load()
        info = self.pm.get('hello')
        self.assertEqual(info.version, '1.2.3')
        self.assertEqual(info.description, 'A test plugin')
        self.assertEqual(info.status, 'loaded')

    def test_directory_without_manifest_skipped(self):
        write_plugin(self.plugins_dir, 'orphan', SIMPLE_TOOL_PLUGIN)
        self.pm.load()
        self.assertIsNone(self.pm.get('orphan'))

    def test_invalid_manifest_is_error(self):
        pdir = self.plugins_dir / 'broken'
        pdir.mkdir(parents=True, exist_ok=True)
        with open(pdir / 'manifest.json', 'w') as f:
            f.write('{not valid json')
        with open(pdir / 'plugin.py', 'w') as f:
            f.write('def register_tools(registry):\n    pass\n')
        self.pm.load()
        info = self.pm.get('broken')
        self.assertEqual(info.status, 'error')
        self.assertIn('invalid manifest', info.error)

    def test_local_wins_over_global(self):
        gdir = self.root / 'global_plugins'
        gdir.mkdir()
        write_plugin(gdir, 'hello', SIMPLE_TOOL_PLUGIN,
                     {'name': 'hello', 'version': '0.1.0'})
        write_plugin(self.plugins_dir, 'hello', SIMPLE_TOOL_PLUGIN,
                     {'name': 'hello', 'version': '9.9.9'})
        self.pm.global_dir = gdir
        self.pm.load()
        info = self.pm.get('hello')
        self.assertEqual(info.version, '9.9.9')
        self.assertFalse(info.global_)


class TestCompatibility(PluginTestBase):

    def test_replio_version_skip(self):
        write_plugin(self.plugins_dir, 'old', 'def register_tools(registry):\n    pass\n',
                     {'name': 'old', 'replio_version': '>=99.0.0'})
        self.pm.load()
        info = self.pm.get('old')
        self.assertEqual(info.status, 'incompatible')
        self.assertIn('99.0.0', info.error)
        reg = ToolRegistry()
        self.pm.register_tools(reg)
        self.assertNotIn('old', reg.names())

    def test_replio_version_ok(self):
        write_plugin(self.plugins_dir, 'cur', 'def register_tools(registry):\n    pass\n',
                     {'name': 'cur', 'replio_version': '>=0.1.0,<99.0.0'})
        self.pm.load()
        self.assertEqual(self.pm.get('cur').status, 'loaded')

    def test_python_version_skip(self):
        write_plugin(self.plugins_dir, 'py', 'def register_tools(registry):\n    pass\n',
                     {'name': 'py', 'python': '>=99.0'})
        self.pm.load()
        self.assertEqual(self.pm.get('py').status, 'incompatible')


class TestPluginsConfig(PluginTestBase):

    def test_allowlist(self):
        write_plugin(self.plugins_dir, 'a', SIMPLE_TOOL_PLUGIN, {'name': 'a'})
        write_plugin(self.plugins_dir, 'b', SIMPLE_TOOL_PLUGIN, {'name': 'b'})
        pm = self.make_pm({'plugins': ['b']})
        pm.load()
        self.assertEqual(pm.get('a').status, 'disabled')
        self.assertEqual(pm.get('b').status, 'loaded')

    def test_empty_means_all(self):
        write_plugin(self.plugins_dir, 'a', SIMPLE_TOOL_PLUGIN, {'name': 'a'})
        write_plugin(self.plugins_dir, 'b', SIMPLE_TOOL_PLUGIN, {'name': 'b'})
        pm = self.make_pm({'plugins': []})
        pm.load()
        self.assertEqual(pm.get('a').status, 'loaded')
        self.assertEqual(pm.get('b').status, 'loaded')

    def test_legacy_enabled_deny_migrated(self):
        write_plugin(self.plugins_dir, 'a', SIMPLE_TOOL_PLUGIN, {'name': 'a'})
        write_plugin(self.plugins_dir, 'b', SIMPLE_TOOL_PLUGIN, {'name': 'b'})
        pm = self.make_pm({'plugins.enabled': ['a'], 'plugins.deny': ['b']})
        pm.load()
        self.assertEqual(pm.get('a').status, 'loaded')
        self.assertEqual(pm.get('b').status, 'disabled')


class TestEntryErrors(PluginTestBase):

    def test_entry_raises_is_error(self):
        write_plugin(self.plugins_dir, 'boom', 'raise RuntimeError("kaboom")\n', {'name': 'boom'})
        self.pm.load()
        info = self.pm.get('boom')
        self.assertEqual(info.status, 'error')
        self.assertIn('kaboom', info.error)

    def test_missing_entry_is_error(self):
        pdir = self.plugins_dir / 'nofile'
        pdir.mkdir(parents=True, exist_ok=True)
        with open(pdir / 'manifest.json', 'w') as f:
            json.dump({'name': 'nofile', 'entry': 'nope.py'}, f)
        self.pm.load()
        info = self.pm.get('nofile')
        self.assertEqual(info.status, 'error')
        self.assertIn('nope.py', info.error)

    def test_one_bad_plugin_does_not_break_others(self):
        write_plugin(self.plugins_dir, 'boom', 'raise RuntimeError("kaboom")\n', {'name': 'boom'})
        write_plugin(self.plugins_dir, 'ok', SIMPLE_TOOL_PLUGIN, {'name': 'ok'})
        self.pm.load()
        self.assertEqual(self.pm.get('boom').status, 'error')
        self.assertEqual(self.pm.get('ok').status, 'loaded')


class TestRegistration(PluginTestBase):

    def test_register_tools_hook(self):
        write_plugin(self.plugins_dir, 'hello', SIMPLE_TOOL_PLUGIN, SIMPLE_MANIFEST)
        self.pm.load()
        reg = ToolRegistry()
        self.pm.register_tools(reg)
        self.assertIn('hello', reg.names())
        self.assertEqual(reg.execute('hello', {}), 'hello from plugin')

    def test_register_providers_hook(self):
        write_plugin(self.plugins_dir, 'prov', PROVIDER_PLUGIN, {'name': 'prov'})
        self.pm.load()
        classes = self.pm.provider_classes()
        self.assertIn('myprovider', classes)
        self.assertEqual(classes['myprovider'].DEFAULT_MODEL, 'my-model')

    def test_register_services_hook(self):
        write_plugin(self.plugins_dir, 'svc', SERVICE_PLUGIN, {'name': 'svc'})
        self.pm.load()
        self.assertEqual(self.pm.service('greet')(), 'hello from service')
        self.assertIsNone(self.pm.service('nonexistent'))

    def test_register_commands_hook(self):
        write_plugin(self.plugins_dir, 'cmd', COMMAND_PLUGIN, {'name': 'cmd'})
        self.pm.load()
        reg = CommandRegistry(object())
        self.pm.register_commands(reg)
        self.assertIn('frobnicate', reg.commands)

    def test_lazy_dep_error_surfaces_pip_guidance(self):
        write_plugin(self.plugins_dir, 'lazy', LAZY_DEP_PLUGIN, {'name': 'lazy'})
        self.pm.load()
        self.assertEqual(self.pm.get('lazy').status, 'loaded')
        reg = ToolRegistry()
        self.pm.register_tools(reg)
        out = reg.execute('uses_dep', {})
        self.assertIn('pip install replio_definitely_missing_pkg', out)

    def test_dep_status_reports_missing(self):
        write_plugin(self.plugins_dir, 'hello', SIMPLE_TOOL_PLUGIN,
                     {'name': 'hello', 'requires': ['replio_definitely_missing_pkg']})
        self.pm.load()
        status = self.pm.dep_status(self.pm.get('hello'))
        self.assertEqual(status, [('replio_definitely_missing_pkg', False)])

    def test_plugin_tool_respects_tool_policy(self):
        write_plugin(self.plugins_dir, 'sec', POLICY_PLUGIN, {'name': 'sec'})
        self.pm.load()
        reg = ToolRegistry()
        self.pm.register_tools(reg)
        self.assertIn('confidential', reg.names())
        policy = ToolPolicy({'read': 'allow'}, deny=['confidential'])
        allowed = {n for n in reg.names() if policy.allowed(n)}
        self.assertNotIn('confidential', allowed)


class TestInstallUpdateUninstall(PluginTestBase):

    def _make_source(self):
        src = self.root / 'src_plugin'
        src.mkdir()
        with open(src / 'manifest.json', 'w') as f:
            json.dump({'name': 'hello', 'version': '0.5.0'}, f)
        with open(src / 'plugin.py', 'w') as f:
            f.write(SIMPLE_TOOL_PLUGIN)
        return src

    def test_install_from_path(self):
        src = self._make_source()
        info = self.pm.install(str(src))
        self.assertEqual(info.name, 'hello')
        installed = self.pm.get('hello')
        self.assertIsNotNone(installed)
        self.assertEqual(installed.version, '0.5.0')
        self.assertEqual(installed.status, 'loaded')
        self.assertTrue((self.plugins_dir / 'hello' / 'manifest.json').exists())
        manifest = json.loads((self.plugins_dir / 'hello' / 'manifest.json').read_text())
        self.assertEqual(manifest['source'], str(src))

    def test_install_missing_source_raises(self):
        with self.assertRaises(PluginError):
            self.pm.install('/nonexistent/plugin/path')

    def test_update_from_path(self):
        src = self._make_source()
        self.pm.install(str(src))
        with open(src / 'plugin.py', 'w') as f:
            f.write(SIMPLE_TOOL_PLUGIN + '\n# v2\n')
        info = self.pm.update('hello')
        self.assertEqual(info.version, '0.5.0')
        content = (self.plugins_dir / 'hello' / 'plugin.py').read_text()
        self.assertIn('# v2', content)

    def test_update_unknown_raises(self):
        with self.assertRaises(PluginError):
            self.pm.update('nope')

    def test_uninstall(self):
        src = self._make_source()
        self.pm.install(str(src))
        self.pm.uninstall('hello')
        self.assertFalse((self.plugins_dir / 'hello').exists())
        self.assertIsNone(self.pm.get('hello'))


class TestEngineIntegration(PluginTestBase):

    def test_engine_loads_plugin_tools(self):
        write_plugin(self.plugins_dir, 'hello', SIMPLE_TOOL_PLUGIN, SIMPLE_MANIFEST)
        from replio.engine import Engine
        engine = Engine(self.config, ui=NullUI())
        engine._init_tooling()
        self.assertIn('hello', engine._tool_registry.names())

    def test_engine_registers_plugin_commands(self):
        write_plugin(self.plugins_dir, 'cmd', COMMAND_PLUGIN, {'name': 'cmd'})
        from replio.engine import Engine
        engine = Engine(self.config, ui=NullUI())
        self.assertIn('frobnicate', engine.registry.commands)

    def test_plugins_slash_command_lists(self):
        write_plugin(self.plugins_dir, 'hello', SIMPLE_TOOL_PLUGIN, SIMPLE_MANIFEST)
        from replio.engine import Engine
        engine = Engine(self.config, ui=NullUI())
        buf = io.StringIO()
        with redirect_stdout(buf):
            engine.registry.dispatch('/plugins')
        self.assertIn('hello', buf.getvalue())


if __name__ == '__main__':
    unittest.main()
