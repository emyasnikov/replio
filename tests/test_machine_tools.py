import unittest
import tempfile
from pathlib import Path

from replio.config import Config
from replio.plugins.manager import PluginManager
from replio.tools.registry import ToolRegistry


class TestMachineTools(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self._cfg_tmp = tempfile.TemporaryDirectory()
        self.pm = PluginManager(Config(path=self._cfg_tmp.name))
        self.pm.load()
        self.registry = ToolRegistry()
        self.pm.register_tools(self.registry)

    def tearDown(self):
        self._tmp.cleanup()
        self._cfg_tmp.cleanup()

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
        self.assertIn('20 lines', out)
        self.assertIn('(showing 5-7)', out)

    def test_read_file_header_reports_total(self):
        (self.root / 'a.txt').write_text('one\ntwo\nthree\n')
        out = self.run_tool('read_file', path=str(self.root / 'a.txt'))
        self.assertIn('3 lines', out)
        self.assertNotIn('(showing', out)
        self.assertIn('1|one', out)
        self.assertIn('3|three', out)

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

    def test_list_dir_depth_recursive(self):
        (self.root / 'src' / 'deep').mkdir(parents=True)
        (self.root / 'src' / 'mod.py').write_text('x')
        (self.root / 'src' / 'deep' / 'leaf.py').write_text('y')
        out = self.run_tool('list_dir', path=str(self.root), depth=3)
        self.assertIn('src/', out)
        self.assertIn('  mod.py', out)
        self.assertIn('  deep/', out)
        self.assertIn('    leaf.py', out)

    def test_list_dir_depth_two_stops_below(self):
        (self.root / 'src' / 'deep').mkdir(parents=True)
        (self.root / 'src' / 'deep' / 'leaf.py').write_text('y')
        out = self.run_tool('list_dir', path=str(self.root), depth=2)
        self.assertIn('src/', out)
        self.assertIn('  deep/', out)
        self.assertNotIn('leaf.py', out)

    def test_list_dir_depth_skips_noise_dirs(self):
        (self.root / '.venv').mkdir()
        (self.root / '.venv' / 'lib.py').write_text('y')
        (self.root / 'a.txt').write_text('x')
        out = self.run_tool('list_dir', path=str(self.root), depth=3)
        self.assertIn('.venv/', out)
        self.assertNotIn('lib.py', out)
        self.assertIn('a.txt', out)

    def test_list_dir_depth_one_matches_flat(self):
        (self.root / 'b.txt').write_text('x')
        (self.root / 'sub').mkdir()
        flat = self.run_tool('list_dir', path=str(self.root))
        explicit = self.run_tool('list_dir', path=str(self.root), depth=1)
        self.assertEqual(flat, explicit)

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

    def test_glob_recursive(self):
        (self.root / 'src').mkdir()
        (self.root / 'src' / 'app.py').write_text('x')
        (self.root / 'src' / 'deep').mkdir()
        (self.root / 'src' / 'deep' / 'mod.py').write_text('y')
        out = self.run_tool('glob', pattern='**/*.py', path=str(self.root))
        self.assertIn('src/app.py', out)
        self.assertIn('src/deep/mod.py', out)

    def test_glob_skips_noise_dirs(self):
        (self.root / 'app.py').write_text('x')
        (self.root / '.venv').mkdir()
        (self.root / '.venv' / 'lib.py').write_text('y')
        (self.root / '__pycache__').mkdir()
        (self.root / '__pycache__' / 'cache.py').write_text('z')
        out = self.run_tool('glob', pattern='**/*.py', path=str(self.root))
        self.assertIn('app.py', out)
        self.assertNotIn('.venv', out)
        self.assertNotIn('cache.py', out)

    def test_glob_dir_marker(self):
        (self.root / 'src').mkdir()
        (self.root / 'src' / 'a.txt').write_text('x')
        out = self.run_tool('glob', pattern='**/*', path=str(self.root))
        self.assertIn('src/', out)

    def test_glob_no_match(self):
        out = self.run_tool('glob', pattern='**/*.rs', path=str(self.root))
        self.assertIn('no matches', out)

    def test_glob_bad_path(self):
        out = self.run_tool('glob', pattern='**/*.py', path=str(self.root / 'nope'))
        self.assertIn('not a directory', out)

    def test_grep_finds_matches(self):
        (self.root / 'a.py').write_text('import os\nvalue = 1\n')
        (self.root / 'b.txt').write_text('no match here\n')
        out = self.run_tool('grep', pattern='value', path=str(self.root))
        self.assertIn('a.py:2:', out)
        self.assertNotIn('b.txt', out)

    def test_grep_glob_filter(self):
        (self.root / 'a.py').write_text('needle\n')
        (self.root / 'b.md').write_text('needle\n')
        out = self.run_tool('grep', pattern='needle', path=str(self.root), glob='*.py')
        self.assertIn('a.py:1:', out)
        self.assertNotIn('b.md', out)

    def test_grep_file_target(self):
        (self.root / 'a.py').write_text('needle here\n')
        out = self.run_tool('grep', pattern='needle', path=str(self.root / 'a.py'))
        self.assertIn('a.py:1:', out)

    def test_grep_no_match(self):
        (self.root / 'a.py').write_text('nothing\n')
        out = self.run_tool('grep', pattern='zzz', path=str(self.root))
        self.assertIn('no matches', out)

    def test_grep_invalid_regex(self):
        out = self.run_tool('grep', pattern='[unclosed', path=str(self.root))
        self.assertIn('invalid regex', out)

    def test_metadata_registered(self):
        expected = {
            'read_file': ('read', 'read', 'path', 'path'),
            'list_dir': ('read', 'list', 'path', 'path'),
            'write_file': ('write', 'edit', 'path', 'path'),
            'run_command': ('exec', 'bash', None, 'command'),
            'glob': ('read', 'list', 'path', 'pattern'),
            'grep': ('read', 'list', 'path', 'pattern'),
        }
        for name, (category, permission, path_arg, key_arg) in expected.items():
            self.assertEqual(self.registry.permission_for(name), permission, name)
            self.assertEqual(self.registry.path_arg_for(name), path_arg, name)
            self.assertEqual(self.registry.key_arg_for(name), key_arg, name)


if __name__ == '__main__':
    unittest.main()
