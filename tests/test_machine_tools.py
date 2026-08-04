import unittest
import tempfile
from pathlib import Path

from replio.tools.registry import ToolRegistry
from replio.tools.machine import register_machine_tools


class TestMachineTools(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.registry = ToolRegistry()
        register_machine_tools(self.registry)

    def tearDown(self):
        self._tmp.cleanup()

    def run_tool(self, name, **args):
        return self.registry.execute(name, args)

    def test_read_file_numbered(self):
        (self.root / 'a.txt').write_text('one\ntwo\nthree\n')
        out = self.run_tool('read_file', path=str(self.root / 'a.txt'))
        self.assertIn('1|one', out)
        self.assertIn('3|three', out)

    def test_read_file_offset_limit(self):
        (self.root / 'a.txt').write_text('\n'.join(f'line{i}' for i in range(1, 21)))
        out = self.run_tool('read_file', path=str(self.root / 'a.txt'), offset=5, limit=3)
        self.assertIn('5|line5', out)
        self.assertIn('7|line7', out)
        self.assertNotIn('line8', out)
        self.assertIn('of 20', out)

    def test_read_file_missing(self):
        out = self.run_tool('read_file', path=str(self.root / 'nope.txt'))
        self.assertIn('not found', out)

    def test_read_file_is_directory(self):
        out = self.run_tool('read_file', path=str(self.root))
        self.assertIn('directory', out)

    def test_list_dir(self):
        (self.root / 'b.txt').write_text('x')
        (self.root / 'sub').mkdir()
        out = self.run_tool('list_dir', path=str(self.root))
        self.assertIn('b.txt', out)
        self.assertIn('sub/', out)

    def test_list_dir_empty(self):
        out = self.run_tool('list_dir', path=str(self.root))
        self.assertIn('(empty directory)', out)

    def test_list_dir_missing(self):
        out = self.run_tool('list_dir', path=str(self.root / 'nope'))
        self.assertIn('not found', out)

    def test_write_file_creates(self):
        out = self.run_tool('write_file', path=str(self.root / 'new.txt'), content='hello')
        self.assertIn('Wrote 5 chars', out)
        self.assertEqual((self.root / 'new.txt').read_text(), 'hello')

    def test_write_file_creates_parents(self):
        self.run_tool('write_file', path=str(self.root / 'deep' / 'dir' / 'f.txt'), content='x')
        self.assertTrue((self.root / 'deep' / 'dir' / 'f.txt').exists())

    def test_write_file_append(self):
        (self.root / 'f.txt').write_text('a')
        self.run_tool('write_file', path=str(self.root / 'f.txt'), content='b', mode='a')
        self.assertEqual((self.root / 'f.txt').read_text(), 'ab')

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

    def test_metadata_registered(self):
        expected = {
            'read_file': ('read', 'read', 'path', 'path'),
            'list_dir': ('read', 'list', 'path', 'path'),
            'write_file': ('write', 'edit', 'path', 'path'),
            'run_command': ('exec', 'bash', None, 'command'),
        }
        for name, (category, permission, path_arg, key_arg) in expected.items():
            self.assertEqual(self.registry.permission_for(name), permission, name)
            self.assertEqual(self.registry.path_arg_for(name), path_arg, name)
            self.assertEqual(self.registry.key_arg_for(name), key_arg, name)


if __name__ == '__main__':
    unittest.main()
