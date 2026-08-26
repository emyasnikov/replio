import importlib.util
import sys
import unittest
import tempfile
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from replio.tools.registry import ToolRegistry


def _load_plugin(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


exec_plugin = _load_plugin('replio_exec_plugin', SRC / 'plugin.py')


class _Cfg:
    def __init__(self, **kw):
        self.data = kw

    def get(self, key, default=None):
        return self.data.get(key, default)


class TestExecTools(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.registry = ToolRegistry()
        exec_plugin.register_tools(self.registry)

    def tearDown(self):
        self._tmp.cleanup()

    def run_tool(self, name, **args):
        return self.registry.execute(name, args)

    def run_tool_cfg(self, name, config, **args):
        return self.registry.execute(name, args, config=config)

    def test_run_command_success(self):
        out = self.run_tool('run_command', command='echo hello', cwd=str(self.root))
        self.assertIn('exit 0', out)
        self.assertIn('hello', out)

    def test_run_command_nonzero_exit(self):
        out = self.run_tool('run_command', command='exit 3', cwd=str(self.root))
        self.assertIn('exit 3', out)

    def test_run_command_timeout(self):
        out = self.run_tool('run_command', command='sleep 5', cwd=str(self.root), timeout=1)
        self.assertIn('timed out', out)

    def test_run_command_missing_cwd(self):
        out = self.run_tool('run_command', command='echo hi',
                            cwd='/definitely/not/a/real/dir')
        self.assertIn("Error: cwd not found: /definitely/not/a/real/dir", out)

    def test_clamp_timeout(self):
        self.assertEqual(exec_plugin._clamp_timeout(10000), exec_plugin.MAX_TIMEOUT)
        self.assertEqual(exec_plugin._clamp_timeout(5), 5)
        self.assertEqual(exec_plugin._clamp_timeout(0), 1)
        self.assertEqual(exec_plugin._clamp_timeout('nonsense'), exec_plugin.DEFAULT_TIMEOUT)
        self.assertEqual(exec_plugin._clamp_timeout(None), exec_plugin.DEFAULT_TIMEOUT)

    def test_run_command_cap_truncates(self):
        out = self.run_tool_cfg('run_command', _Cfg(tool_max_result_chars=20),
                                command='seq 1 1000', cwd=str(self.root))
        self.assertIn('... (truncated)', out)
        self.assertNotIn('\n1000', out)

    def test_metadata_registered(self):
        self.assertEqual(self.registry.permission_for('run_command'), 'bash')
        self.assertEqual(self.registry.path_arg_for('run_command'), None)
        self.assertEqual(self.registry.key_arg_for('run_command'), 'command')
        self.assertTrue(self.registry.echo_for('run_command'))


if __name__ == '__main__':
    unittest.main()