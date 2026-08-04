import unittest
import tempfile
from pathlib import Path

from replio.tools.policy import ToolPolicy


class TestToolPolicy(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def policy(self, **kw):
        return ToolPolicy(worktree=self.root, **kw)

    def test_default_allow_inside_worktree(self):
        p = self.policy(permissions={'read': 'allow'})
        inside = self.root / 'file.txt'
        self.assertEqual(p.action('read_file', 'read', str(inside)), 'allow')

    def test_external_directory_escalates_to_ask(self):
        p = self.policy(permissions={'read': 'allow'})
        outside = self.root.parent / 'elsewhere' / 'file.txt'
        self.assertEqual(p.action('read_file', 'read', str(outside)), 'ask')

    def test_external_directory_without_path_stays_allow(self):
        p = self.policy(permissions={'read': 'allow'})
        self.assertEqual(p.action('read_file', 'read', None), 'allow')

    def test_deny_list_wins(self):
        p = self.policy(permissions={'read': 'allow'}, deny=['read_file'])
        self.assertEqual(p.action('read_file', 'read', str(self.root)), 'deny')

    def test_allow_list_whitelists(self):
        p = self.policy(permissions={'read': 'allow', 'list': 'allow'}, allow=['list_dir'])
        self.assertEqual(p.action('read_file', 'read', str(self.root)), 'deny')
        self.assertEqual(p.action('list_dir', 'list', str(self.root)), 'allow')

    def test_ask_permission_key(self):
        p = self.policy(permissions={'bash': 'ask'})
        self.assertEqual(p.action('run_command', 'bash'), 'ask')

    def test_unknown_permission_defaults_to_ask(self):
        p = self.policy(permissions={})
        self.assertEqual(p.action('some_tool', 'nope'), 'ask')

    def test_deny_never_escalates_to_ask(self):
        p = self.policy(permissions={'edit': 'deny'})
        outside = self.root.parent / 'elsewhere' / 'f.txt'
        self.assertEqual(p.action('write_file', 'edit', str(outside)), 'deny')

    def test_needs_confirm(self):
        p = self.policy(permissions={'bash': 'ask', 'edit': 'allow'})
        self.assertTrue(p.needs_confirm('run_command', 'bash'))
        self.assertFalse(p.needs_confirm('write_file', 'edit', str(self.root / 'f.txt')))
        self.assertTrue(p.needs_confirm(
            'write_file', 'edit', str(self.root.parent / 'f.txt')))

    def test_allowed(self):
        p = self.policy(permissions={}, deny=['run_command'])
        self.assertFalse(p.allowed('run_command'))
        self.assertTrue(p.allowed('read_file'))
        whitelist = self.policy(permissions={}, allow=['read_file'])
        self.assertTrue(whitelist.allowed('read_file'))
        self.assertFalse(whitelist.allowed('list_dir'))

    def test_relative_path_against_worktree(self):
        import os
        p = self.policy(permissions={'read': 'allow'})
        cwd = os.getcwd()
        try:
            os.chdir(self.root)
            self.assertEqual(p.action('read_file', 'read', 'file.txt'), 'allow')
        finally:
            os.chdir(cwd)

    def test_expands_user(self):
        import os
        home = Path(os.path.expanduser('~'))
        if home == self.root.resolve():
            self.skipTest('home equals worktree')
        p = self.policy(permissions={'read': 'allow'})
        self.assertEqual(p.action('read_file', 'read', '~/x.txt'), 'ask')


if __name__ == '__main__':
    unittest.main()
