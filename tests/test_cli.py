import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from replio.cli import cmd_run, cmd_export, cmd_models, cmd_plugins
from replio.main import main
from replio import get_version
from replio.sessions.manager import Session


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
                    base_url=None, mode=None)
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

    def test_run_overrides_do_not_persist(self):
        self._run([[{'type': 'token', 'content': 'x'},
                    {'type': 'done', 'reason': 'stop'}]],
                  provider='ollama', model='override-model',
                  base_url='https://override.example')
        cfg = Path(self.tmp.name) / '.replio' / 'config.json'
        self.assertFalse(cfg.exists())

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

    def test_run_mode_plan_filters_schema(self):
        captured = {}

        def _factory_rec(rounds):
            def _f(**kwargs):
                p = MagicMock()
                p.chat.side_effect = rounds
                captured['provider'] = p
                return p
            _f.DEFAULT_BASE_URL = 'https://fake.api.com'
            _f.DEFAULT_MODEL = 'fake-model'
            return _f
        rounds = [[{'type': 'token', 'content': 'plan answer'},
                   {'type': 'done', 'reason': 'stop'}]]
        with patch('replio.providers.PROVIDERS', {'ollama': _factory_rec(rounds)}):
            out = io.StringIO()
            with patch('sys.stdout', new=out):
                rc = cmd_run(self._args(mode='plan'))
        self.assertEqual(rc, 0)
        data = json.loads(out.getvalue())
        self.assertEqual(data['content'], 'plan answer')
        tools = captured['provider'].chat.call_args.kwargs['tools']
        names = [s['function']['name'] for s in tools]
        self.assertNotIn('file_write', names)
        self.assertNotIn('run_command', names)
        self.assertIn('file_read', names)
        msgs = captured['provider'].chat.call_args.args[0]
        self.assertIn('plan mode', msgs[0]['content'])

    def test_run_mode_build_keeps_write_tools(self):
        captured = {}

        def _factory_rec(rounds):
            def _f(**kwargs):
                p = MagicMock()
                p.chat.side_effect = rounds
                captured['provider'] = p
                return p
            _f.DEFAULT_BASE_URL = 'https://fake.api.com'
            _f.DEFAULT_MODEL = 'fake-model'
            return _f
        rounds = [[{'type': 'token', 'content': 'x'},
                   {'type': 'done', 'reason': 'stop'}]]
        with patch('replio.providers.PROVIDERS', {'ollama': _factory_rec(rounds)}):
            out = io.StringIO()
            with patch('sys.stdout', new=out):
                cmd_run(self._args())
        tools = captured['provider'].chat.call_args.kwargs['tools']
        names = [s['function']['name'] for s in tools]
        self.assertIn('file_write', names)
        self.assertIn('run_command', names)


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

    def test_plugins_list_shows_bundled(self):
        rc, out, _ = self._capture(self._args())
        self.assertEqual(rc, 0)
        self.assertIn('replio-core-web', out)
        self.assertIn('bundled', out)

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


class TestCliExport(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = self.tmp.name
        sessions = Path(self.path) / '.replio' / 'sessions'
        sessions.mkdir(parents=True, exist_ok=True)
        s = Session('alpha')
        s.add_message('user', 'hello')
        s.add_message('assistant', 'hi there')
        with open(sessions / 'alpha.json', 'w') as f:
            json.dump(s.to_dict(), f)

    def tearDown(self):
        self.tmp.cleanup()

    def _args(self, **kw):
        base = dict(name='alpha', out=None, path=self.path)
        base.update(kw)
        return SimpleNamespace(**base)

    def _capture(self, args):
        out = io.StringIO()
        err = io.StringIO()
        with patch('sys.stdout', new=out), patch('sys.stderr', new=err):
            rc = cmd_export(args)
        return rc, out.getvalue(), err.getvalue()

    def test_export_writes_default_file(self):
        rc, out, _ = self._capture(self._args())
        self.assertEqual(rc, 0)
        path = (Path(self.path) / '.replio' / 'exports' / 'alpha.md').resolve()
        self.assertTrue(path.exists())
        self.assertIn('# Session: alpha', path.read_text())
        self.assertIn(f'Exported session: alpha -> {path}', out)

    def test_export_stdout(self):
        rc, out, _ = self._capture(self._args(out='-'))
        self.assertEqual(rc, 0)
        self.assertIn('# Session: alpha', out)
        self.assertIn('hello', out)
        self.assertIn('hi there', out)

    def test_export_custom_out(self):
        target = Path(self.path) / 'out' / 'custom.md'
        rc, _, _ = self._capture(self._args(out=str(target)))
        self.assertEqual(rc, 0)
        self.assertTrue(target.exists())
        self.assertIn('# Session: alpha', target.read_text())

    def test_export_not_found(self):
        rc, _, err = self._capture(self._args(name='nosuch'))
        self.assertEqual(rc, 1)
        self.assertIn('Session not found: nosuch', err)

    def test_export_main_dispatch(self):
        out = io.StringIO()
        with patch('sys.stdout', new=out):
            rc = main(['export', 'alpha', '--path', self.path])
        self.assertEqual(rc, 0)
        self.assertIn('Exported session: alpha', out.getvalue())


class TestCliModels(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def _args(self, **kw):
        base = dict(path=self.path)
        base.update(kw)
        return SimpleNamespace(**base)

    def _capture(self, args, list_result):
        engine = MagicMock()
        engine.list_models.return_value = list_result
        with patch('replio.cli.Engine', return_value=engine):
            out = io.StringIO()
            err = io.StringIO()
            with patch('sys.stdout', new=out), patch('sys.stderr', new=err):
                rc = cmd_models(args)
        return rc, out.getvalue(), err.getvalue()

    def test_models_lists_available(self):
        rc, out, _ = self._capture(self._args(), (['m1', 'm2'], None))
        self.assertEqual(rc, 0)
        self.assertIn('2 models available from', out)
        self.assertIn('- m1', out)

    def test_models_error_exit_code(self):
        rc, _, err = self._capture(self._args(), ([], 'HTTP 500: boom'))
        self.assertEqual(rc, 1)
        self.assertIn('HTTP 500: boom', err)

    def test_models_empty(self):
        rc, out, _ = self._capture(self._args(), ([], None))
        self.assertEqual(rc, 0)
        self.assertIn('No models listed', out)

    def test_models_main_dispatch(self):
        engine = MagicMock()
        engine.list_models.return_value = (['m1'], None)
        with patch('replio.cli.Engine', return_value=engine):
            out = io.StringIO()
            with patch('sys.stdout', new=out):
                rc = main(['models', '--path', self.path])
        self.assertEqual(rc, 0)
        self.assertIn('1 models available from', out.getvalue())


class TestCliEval(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = self.tmp.name
        self._prev = None
        from replio.config import Config
        self._prev = Config.GLOBAL_DIR
        Config.GLOBAL_DIR = Path(self.path) / 'home'

    def tearDown(self):
        from replio.config import Config
        Config.GLOBAL_DIR = self._prev
        import shutil
        shutil.rmtree(self.path, ignore_errors=True)

    def _fixture(self, **data):
        eval_dir = Path(self.path) / '.replio' / 'eval'
        eval_dir.mkdir(parents=True, exist_ok=True)
        (eval_dir / 't.json').write_text(json.dumps(data))

    def test_eval_list(self):
        self._fixture(task='List the directory', expected=['list_dir'])
        out = io.StringIO()
        with patch('sys.stdout', new=out):
            rc = main(['eval', '--path', self.path, 'list'])
        self.assertEqual(rc, 0)
        self.assertIn('t - List the directory', out.getvalue())

    def test_eval_run_table(self):
        self._fixture(task='List the directory', expected=['list_dir'],
                      verifier={'exact': ['list_dir']})
        rounds = [
            [{'type': 'tool_calls', 'tool_calls': [
                {'id': 'c1', 'type': 'function',
                 'function': {'name': 'list_dir',
                              'arguments': json.dumps({'path': '.'})}},
            ]}],
            [{'type': 'token', 'content': 'ok'},
             {'type': 'done', 'reason': 'stop',
              'usage': {'prompt_tokens': 4, 'completion_tokens': 1}}],
        ]
        with patch('replio.providers.PROVIDERS', {'ollama': _factory(rounds)}):
            out = io.StringIO()
            with patch('sys.stdout', new=out):
                rc = main(['eval', '--path', self.path, 'run', '--fixture', 't'])
        self.assertEqual(rc, 0)
        self.assertIn('accuracy 1.00', out.getvalue())
        self.assertIn('t', out.getvalue())

    def test_eval_run_json_output(self):
        self._fixture(task='List the directory', expected=['list_dir'])
        rounds = [
            [{'type': 'tool_calls', 'tool_calls': [
                {'id': 'c1', 'type': 'function',
                 'function': {'name': 'list_dir',
                              'arguments': json.dumps({'path': '.'})}},
            ]}],
            [{'type': 'token', 'content': 'ok'},
             {'type': 'done', 'reason': 'stop'}],
        ]
        with patch('replio.providers.PROVIDERS', {'ollama': _factory(rounds)}):
            out = io.StringIO()
            with patch('sys.stdout', new=out):
                rc = main(['eval', '--path', self.path, 'run', '--fixture', 't',
                           '--output', 'json'])
        self.assertEqual(rc, 0)
        data = json.loads(out.getvalue())
        self.assertEqual(data['summary']['fixtures'], 1)
        self.assertEqual(data['results'][0]['names'], ['list_dir'])

    def test_eval_run_no_fixtures_errors(self):
        err = io.StringIO()
        with patch('sys.stderr', new=err):
            out = io.StringIO()
            with patch('sys.stdout', new=out):
                rc = main(['eval', '--path', self.path, 'run', '--fixture', 'zz'])
        self.assertEqual(rc, 1)
        self.assertIn('No eval fixtures found', err.getvalue())


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
