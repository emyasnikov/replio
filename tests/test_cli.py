import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from replio.cli import cmd_run, cmd_plugins
from replio.main import main
from replio import get_version


def _factory(rounds):
    def _f(**kwargs):
        p = MagicMock()
        p.chat.side_effect = rounds
        return p
    _f.DEFAULT_BASE_URL = 'https://fake.api.com'
    _f.DEFAULT_MODEL = 'fake-model'
    return _f


class TestCliRun(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def _args(self, **kw):
        base = dict(prompt='hello', output='json', session_id=None, approve=None,
                    verbose=False, path=self.tmp.name, provider=None, model=None,
                    base_url=None)
        base.update(kw)
        return SimpleNamespace(**base)

    def _run(self, rounds, **kw):
        with patch('replio.providers.PROVIDERS', {'ollama': _factory(rounds)}):
            out = io.StringIO()
            with patch('sys.stdout', new=out):
                rc = cmd_run(self._args(**kw))
        return rc, out.getvalue()

    def test_run_json_output(self):
        rc, out = self._run([[{'type': 'token', 'content': 'cli answer'},
                              {'type': 'done', 'reason': 'stop'}]])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data['content'], 'cli answer')
        self.assertEqual(data['status'], 'ok')

    def test_run_stdout_is_pure_json(self):
        _, out = self._run([[{'type': 'token', 'content': 'answer'},
                             {'type': 'done', 'reason': 'stop'}]])
        json.loads(out)
        self.assertNotIn('\x1b', out)

    def test_run_text_mode_streams_content(self):
        rc, out = self._run([[{'type': 'token', 'content': 'plain answer'},
                              {'type': 'done', 'reason': 'stop'}]], output='text')
        self.assertEqual(rc, 0)
        self.assertIn('plain answer', out)

    def test_run_session_id_persists(self):
        self._run([[{'type': 'token', 'content': 'answer'},
                    {'type': 'done', 'reason': 'stop'}]], session_id='persist')
        sess = Path(self.tmp.name) / '.replio' / 'sessions' / 'persist.json'
        self.assertTrue(sess.exists())

    def test_run_error_exit_code(self):
        rc, _ = self._run([[{'type': 'error', 'code': 500, 'message': 'boom'}]])
        self.assertEqual(rc, 1)

    def test_run_overrides_apply(self):
        captured = {}

        def _factory_rec(**kwargs):
            captured.update(kwargs)
            p = MagicMock()
            p.chat.side_effect = [[{'type': 'token', 'content': 'x'},
                                   {'type': 'done', 'reason': 'stop'}]]
            return p
        _factory_rec.DEFAULT_BASE_URL = 'https://fake.api.com'
        _factory_rec.DEFAULT_MODEL = 'fake-model'
        with patch('replio.providers.PROVIDERS', {'ollama': _factory_rec}):
            out = io.StringIO()
            with patch('sys.stdout', new=out):
                cmd_run(self._args(provider='ollama', model='my-model',
                                   base_url='https://x.example'))
        self.assertEqual(captured['model'], 'my-model')
        self.assertEqual(captured['base_url'], 'https://x.example')

    def test_run_yes_approves_asks(self):
        tool_round = [{'type': 'tool_calls', 'tool_calls': [{
            'id': 'c1', 'type': 'function',
            'function': {'name': 'run_command', 'arguments': '{"command": "echo hi"}'},
        }]}]
        content_round = [{'type': 'token', 'content': 'ran it'},
                         {'type': 'done', 'reason': 'stop'}]
        rc, out = self._run([tool_round, content_round], approve=True)
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data['content'], 'ran it')
        self.assertEqual(len(data['tool_calls']), 1)

    def test_run_default_denies_asks(self):
        tool_round = [{'type': 'tool_calls', 'tool_calls': [{
            'id': 'c1', 'type': 'function',
            'function': {'name': 'run_command', 'arguments': '{"command": "echo hi"}'},
        }]}]
        content_round = [{'type': 'token', 'content': 'skipped'},
                         {'type': 'done', 'reason': 'stop'}]
        rc, out = self._run([tool_round, content_round])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(len(data['tool_calls']), 1)


class TestCliPlugins(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def _args(self, **kw):
        base = dict(path=self.path, action='list', source=None,
                    global_=False, deps=False, name=None)
        base.update(kw)
        return SimpleNamespace(**base)

    def _capture(self, args):
        out = io.StringIO()
        err = io.StringIO()
        with patch('sys.stdout', new=out), patch('sys.stderr', new=err):
            rc = cmd_plugins(args)
        return rc, out.getvalue(), err.getvalue()

    def test_plugins_list_empty(self):
        rc, out, _ = self._capture(self._args())
        self.assertEqual(rc, 0)
        self.assertIn('no plugins installed', out)

    def test_plugins_install_list_uninstall(self):
        src = Path(self.path) / 'src_plugin'
        (src / 'manifest.json').parent.mkdir(parents=True, exist_ok=True)
        with open(src / 'manifest.json', 'w') as f:
            json.dump({'name': 'hello', 'version': '1.0.0'}, f)
        with open(src / 'plugin.py', 'w') as f:
            f.write('def register_tools(registry):\n    pass\n')

        rc, out, _ = self._capture(self._args(action='install', source=str(src)))
        self.assertEqual(rc, 0)
        self.assertIn('hello', out)

        rc, out, _ = self._capture(self._args(action='list'))
        self.assertEqual(rc, 0)
        self.assertIn('hello', out)

        rc, _, _ = self._capture(self._args(action='uninstall', name='hello'))
        self.assertEqual(rc, 0)
        self.assertFalse((Path(self.path) / '.replio' / 'plugins' / 'hello').exists())

    def test_plugins_install_missing_source_errors(self):
        rc, _, err = self._capture(self._args(action='install',
                                              source='/nonexistent/path'))
        self.assertEqual(rc, 1)
        self.assertIn('Error', err)


class TestCliVersion(unittest.TestCase):

    def test_version_long_flag(self):
        out = io.StringIO()
        with patch('sys.stdout', new=out):
            with self.assertRaises(SystemExit) as ctx:
                main(['--version'])
        self.assertEqual(ctx.exception.code, 0)
        self.assertIn(get_version(), out.getvalue())

    def test_version_short_flag(self):
        out = io.StringIO()
        with patch('sys.stdout', new=out):
            with self.assertRaises(SystemExit) as ctx:
                main(['-v'])
        self.assertEqual(ctx.exception.code, 0)
        self.assertIn(get_version(), out.getvalue())


if __name__ == '__main__':
    unittest.main()
