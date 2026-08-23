import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from replio.config import Config
from replio.engine import Engine
from replio.plugins.manager import PluginManager
from replio.sessions.manager import SessionManager
from replio.ui import HeadlessUI, NullUI


def make_engine(config_data: dict | None = None) -> Engine:
    temp_dir = tempfile.TemporaryDirectory()
    data = {
        'tool_calling': True,
        'provider': 'ollama',
        'model': 'test-model',
        'base_url': 'https://test.api.com',
        'api_key': '',
        'temperature': 0.7,
        'max_tokens': 2048,
    }
    if config_data:
        data.update(config_data)
    config_dir = Path(temp_dir.name) / '.replio'
    config_dir.mkdir(parents=True, exist_ok=True)
    with open(config_dir / 'config.json', 'w') as f:
        json.dump(data, f)

    config = Config(path=temp_dir.name)
    engine = Engine.__new__(Engine)
    engine.config = config
    engine.provider = MagicMock()
    sessions_dir = config.local_path.parent / 'sessions'
    engine.sessions = SessionManager(sessions_dir)
    engine.current_session = engine.sessions.create()
    engine._tool_registry = None
    engine._plugin_manager = PluginManager(config)
    engine._plugin_manager.load()
    engine._tmp = temp_dir
    return engine


class _CaptureUI:
    def __init__(self):
        self.labels = []

    def activity(self, glyph, verb, label, body):
        self.labels.append(f'{glyph} {verb} {label}')

    def tool_status(self, name, value, body):
        self.labels.append(f'[{name}: {value}]')

    def tool_error(self, msg):
        self.labels.append(f'! {msg.split(chr(10), 1)[0]}')

    def confirm(self, name, label):
        self.labels.append(f'confirm: {label}')
        return True


class TestEngine(unittest.TestCase):

    def setUp(self):
        self.engine = make_engine()

    def tearDown(self):
        self.engine._tmp.cleanup()

    def test_reinit_provider_uses_registry_api_key(self):
        self.engine.models.put('ollama', 'https://test.api.com',
                               'test-model', 'reg-key')
        self.engine.config.apply('api_key', 'cfg-key')
        self.engine._reinit_provider()
        self.assertEqual(self.engine.provider.api_key, 'reg-key')

    def test_reinit_provider_falls_back_to_config_api_key(self):
        self.engine.config.apply('api_key', 'cfg-key')
        self.assertIsNone(self.engine.models.find(
            'ollama', 'https://test.api.com', 'test-model'))
        self.engine._reinit_provider()
        self.assertEqual(self.engine.provider.api_key, 'cfg-key')

    def test_chat_returns_turn_result(self):
        self.engine.provider.chat.return_value = [
            {'type': 'token', 'content': 'Hello world'},
            {'type': 'done', 'reason': 'stop'},
        ]
        result = self.engine.chat('hi')
        self.assertEqual(result.content, 'Hello world')
        self.assertEqual(result.status, 'ok')
        self.assertEqual(result.provider, 'ollama')
        self.assertEqual(result.session, self.engine.current_session.name)
        roles = [m['role'] for m in self.engine.current_session.messages]
        self.assertEqual(roles, ['user', 'assistant'])
        self.assertEqual(result.tool_calls, [])
        self.assertEqual(result.errors, [])

    def test_thinking_separated_from_content(self):
        self.engine.provider.chat.return_value = [
            {'type': 'token', 'content': '<thinking>hmm</thinking>Answer'},
            {'type': 'done', 'reason': 'stop'},
        ]
        result = self.engine.chat('q')
        self.assertEqual(result.content, 'Answer')
        self.assertEqual(result.thinking, '<thinking>hmm')

    def test_provider_thinking_event_accumulates(self):
        self.engine.provider.chat.return_value = [
            {'type': 'thinking', 'content': 'reasoning'},
            {'type': 'token', 'content': 'Answer'},
            {'type': 'done', 'reason': 'stop'},
        ]
        result = self.engine.chat('q')
        self.assertEqual(result.thinking, 'reasoning')
        self.assertEqual(result.content, 'Answer')

    def test_reasoning_and_thinking_persisted_to_session(self):
        self.engine.config.set('reasoning', 'high')
        self.engine.provider.chat.return_value = [
            {'type': 'thinking', 'content': 'secret reasoning'},
            {'type': 'token', 'content': 'Answer'},
            {'type': 'done', 'reason': 'stop'},
        ]
        result = self.engine.chat('q')
        assistant = [m for m in self.engine.current_session.messages
                     if m['role'] == 'assistant'][0]
        self.assertEqual(assistant['thinking'], 'secret reasoning')
        self.assertEqual(assistant['reasoning'], 'high')

    def test_reasoning_persisted_when_thinking_hidden_from_display(self):
        self.engine.config.set('show_thinking', False)
        self.engine.config.set('reasoning', 'auto')
        self.engine.provider.chat.return_value = [
            {'type': 'thinking', 'content': 'still logged'},
            {'type': 'token', 'content': 'Answer'},
            {'type': 'done', 'reason': 'stop'},
        ]
        self.engine.chat('q')
        assistant = [m for m in self.engine.current_session.messages
                     if m['role'] == 'assistant'][0]
        self.assertEqual(assistant['thinking'], 'still logged')
        self.assertEqual(assistant['reasoning'], 'auto')

    def test_error_status_and_errors(self):
        self.engine.provider.chat.return_value = [
            {'type': 'error', 'code': 401, 'message': 'Unauthorized'},
        ]
        result = self.engine.chat('q')
        self.assertEqual(result.status, 'error')
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(result.errors[0]['code'], 401)
        self.assertEqual(result.errors[0]['message'], 'Unauthorized')

    def test_auto_name_session_transliterates_non_ascii(self):
        self.engine.provider.chat.return_value = [
            {'type': 'token', 'content': 'Answer'},
            {'type': 'done', 'reason': 'stop'},
        ]
        self.engine.chat('Lies die Datei und prüfe sie')
        name = self.engine.current_session.name
        self.assertIn('_lies_die_datei_und_prufe', name)
        self.assertTrue(all(ord(c) < 128 for c in name))

    def test_auto_name_session_drops_non_alnum(self):
        self.engine.provider.chat.return_value = [
            {'type': 'token', 'content': 'Answer'},
            {'type': 'done', 'reason': 'stop'},
        ]
        self.engine.chat('what is 2+2? and <b>html</b>')
        name = self.engine.current_session.name
        self.assertIn('_what_is_22_and', name)

    def test_load_or_create_session_persists_and_reloads(self):
        self.engine.load_or_create_session('foo')
        self.assertEqual(self.engine.current_session.name, 'foo')
        self.engine.provider.chat.return_value = [
            {'type': 'token', 'content': 'Answer'},
            {'type': 'done', 'reason': 'stop'},
        ]
        self.engine.chat('q', autoname=False)
        self.assertEqual(self.engine.current_session.name, 'foo')
        self.assertTrue((self.engine.sessions.sessions_dir / 'foo.json').exists())
        self.engine.load_or_create_session('foo')
        self.assertEqual(self.engine.current_session.name, 'foo')
        self.assertEqual(len(self.engine.current_session.messages), 2)

    def test_headless_confirm_policy(self):
        self.engine._init_tooling()
        self.engine._ui = HeadlessUI(auto='deny')
        out = self.engine._run_tool('run_command', {'command': 'echo hi'})
        self.assertEqual(out, '[cancelled] User declined the run_command call')
        self.engine._ui = HeadlessUI(auto='allow')
        self.assertEqual(self.engine._confirm_tool('run_command', {'command': 'echo hi'}), True)

    def test_show_tool_status_renders_params_when_enabled(self):
        ui = _CaptureUI()
        self.engine._init_tooling()
        self.engine._ui = ui
        self.engine._show_tool_status(
            'run_command', {'command': 'ls', 'cwd': '/workspace', 'timeout': 10000})
        self.assertEqual(ui.labels, ['$ Run ls [cwd=/workspace, timeout=10000]'])

    def test_show_tool_status_omits_params_when_disabled(self):
        ui = _CaptureUI()
        self.engine._init_tooling()
        self.engine._ui = ui
        self.engine.config.set('glyph_params', False)
        self.engine._show_tool_status('run_command', {'command': 'ls', 'cwd': '/workspace'})
        self.assertEqual(ui.labels, ['$ Run ls'])

    def test_confirm_label_includes_params(self):
        ui = _CaptureUI()
        self.engine._init_tooling()
        self.engine._ui = ui
        self.engine._confirm_tool('run_command', {'command': 'ls', 'cwd': '/x'})
        self.assertEqual(ui.labels, ['confirm: run_command ls [cwd=/x]'])

    def test_run_tool_error_renders_error_line(self):
        ui = _CaptureUI()
        self.engine._init_tooling()
        self.engine._ui = ui
        out = self.engine._run_tool('read_file', {'path': '/definitely/not/here.txt'})
        self.assertIn('Error: file not found', out)
        self.assertEqual(ui.labels, [
            'confirm: read_file /definitely/not/here.txt',
            '← Read /definitely/not/here.txt',
            '! Error: file not found: /definitely/not/here.txt',
        ])

    def test_run_tool_error_suppressed_when_hidden(self):
        ui = _CaptureUI()
        self.engine._init_tooling()
        self.engine._ui = ui
        self.engine.config.set('show_errors', False)
        self.engine._run_tool('read_file', {'path': '/definitely/not/here.txt'})
        self.assertEqual(ui.labels, [
            'confirm: read_file /definitely/not/here.txt',
            '← Read /definitely/not/here.txt',
        ])

    def test_run_tool_success_no_error_line(self):
        ui = _CaptureUI()
        self.engine._init_tooling()
        self.engine._ui = ui
        self.engine._run_tool('run_command', {'command': 'echo hi'})
        self.assertEqual(ui.labels, ['confirm: run_command echo hi', '$ Run echo hi'])
        self.assertFalse(any(l.startswith('! ') for l in ui.labels))

    def test_denied_ask_tool_feeds_cancelled_result(self):
        self.engine.provider.chat.side_effect = [
            [{'type': 'tool_calls', 'tool_calls': [{
                'id': 'c1', 'type': 'function',
                'function': {'name': 'run_command', 'arguments': '{"command": "echo hi"}'},
            }]}],
            [{'type': 'token', 'content': 'Final answer'},
             {'type': 'done', 'reason': 'stop'}],
        ]
        result = self.engine.chat('q')
        tool_msgs = [m for m in self.engine.current_session.messages if m['role'] == 'tool']
        self.assertEqual(len(tool_msgs), 1)
        self.assertTrue(tool_msgs[0]['content'].startswith('[cancelled]'))
        self.assertEqual(result.content, 'Final answer')
        self.assertEqual(result.tool_calls, [{'name': 'run_command', 'arguments': {'command': 'echo hi'}}])

    def test_turn_result_to_dict_json_serializable(self):
        self.engine.provider.chat.return_value = [
            {'type': 'token', 'content': 'Hello'},
            {'type': 'done', 'reason': 'stop', 'usage': {'prompt_tokens': 10}},
        ]
        result = self.engine.chat('q')
        d = result.to_dict()
        self.assertEqual(d['content'], 'Hello')
        self.assertEqual(d['usage'], {'prompt_tokens': 10})
        self.assertIn('session', d)
        self.assertIn('status', d)
        json.dumps(d)


class _RecordUI(NullUI):
    def __init__(self):
        self.calls = []

    def thinking(self, text):
        self.calls.append(('thinking', text))

    def thinking_begin(self):
        self.calls.append(('begin',))

    def thinking_end(self, duration):
        self.calls.append(('end', duration))


class TestEngineCheckConnection(unittest.TestCase):

    def setUp(self):
        self.engine = make_engine()

    def tearDown(self):
        self.engine._tmp.cleanup()

    def _factory(self, models, error=None):
        captured = {}

        def _f(**kwargs):
            captured.update(kwargs)
            p = MagicMock()
            p._fetch_models.return_value = (list(models), error)
            return p
        _f.DEFAULT_BASE_URL = 'https://test.api.com'
        _f.DEFAULT_MODEL = 'test-model'
        _f.captured = captured
        return _f

    def test_check_connection_resolves_and_probes(self):
        factory = self._factory(['m1', 'm2'])
        with patch('replio.providers.PROVIDERS', {'ollama': factory}):
            ok, msg, models = self.engine.check_connection()
        self.assertTrue(ok)
        self.assertIn('2 models available', msg)
        self.assertEqual(models, ['m1', 'm2'])
        self.assertEqual(factory.captured['base_url'], 'https://test.api.com')
        self.assertEqual(factory.captured['model'], 'test-model')
        self.assertEqual(factory.captured['api_key'], '')

    def test_check_connection_model_mismatch_note(self):
        factory = self._factory(['a', 'b'])
        with patch('replio.providers.PROVIDERS', {'ollama': factory}):
            ok, msg, models = self.engine.check_connection(model='zzz')
        self.assertTrue(ok)
        self.assertIn('"zzz" not in the model list', msg)
        self.assertEqual(models, ['a', 'b'])

    def test_check_connection_overrides_win(self):
        factory = self._factory([], error='HTTP 401: bad')
        with patch('replio.providers.PROVIDERS', {'ollama': factory}):
            ok, msg, models = self.engine.check_connection(
                base_url='https://other.example', api_key='sk-new', model='m2')
        self.assertFalse(ok)
        self.assertEqual(msg, 'HTTP 401: bad')
        self.assertEqual(models, [])
        self.assertEqual(factory.captured['base_url'], 'https://other.example')
        self.assertEqual(factory.captured['api_key'], 'sk-new')
        self.assertEqual(factory.captured['model'], 'm2')

    def test_check_connection_unknown_factory(self):
        with patch('replio.providers.PROVIDERS', {}):
            ok, msg, models = self.engine.check_connection(
                provider='nope', base_url='http://localhost:11434')
        self.assertFalse(ok)
        self.assertIn('No provider registered', msg)
        self.assertEqual(models, [])

    def test_check_connection_does_not_mutate_state(self):
        before = self.engine.provider
        factory = self._factory(['ok-model'])
        with patch('replio.providers.PROVIDERS', {'ollama': factory}):
            self.engine.check_connection(base_url='https://other.example')
        self.assertIs(self.engine.provider, before)
        self.assertEqual(self.engine.config.get('base_url'), 'https://test.api.com')

    def test_check_connection_detects_from_base_url(self):
        factory = self._factory(['g1'])
        with patch('replio.providers.PROVIDERS', {'groq': factory}):
            ok, msg, _ = self.engine.check_connection(
                provider='nope', base_url='https://api.groq.com/openai/v1')
        self.assertTrue(ok)
        self.assertEqual(factory.captured['base_url'], 'https://api.groq.com/openai/v1')

    def test_list_models_returns_models(self):
        factory = self._factory(['m1', 'm2'])
        with patch('replio.providers.PROVIDERS', {'ollama': factory}):
            models, error = self.engine.list_models()
        self.assertIsNone(error)
        self.assertEqual(models, ['m1', 'm2'])

    def test_list_models_returns_error(self):
        factory = self._factory([], error='HTTP 403: forbidden')
        with patch('replio.providers.PROVIDERS', {'ollama': factory}):
            models, error = self.engine.list_models()
        self.assertEqual(models, [])
        self.assertEqual(error, 'HTTP 403: forbidden')

    def test_list_models_unknown_factory(self):
        with patch('replio.providers.PROVIDERS', {}):
            models, error = self.engine.list_models(
                provider='nope', base_url='http://localhost:11434')
        self.assertEqual(models, [])
        self.assertIn('No provider registered', error)

    def test_list_models_respects_overrides(self):
        factory = self._factory(['x'])
        with patch('replio.providers.PROVIDERS', {'ollama': factory}):
            self.engine.list_models(base_url='https://other.example')
        self.assertEqual(factory.captured['base_url'], 'https://other.example')


class TestEngineSinks(unittest.TestCase):

    def test_null_ui_confirm_denies(self):
        from replio.ui import NullUI
        self.assertEqual(NullUI().confirm('x', 'x'), False)

    def test_headless_ui_auto(self):
        self.assertEqual(HeadlessUI(auto='allow').confirm('x', 'x'), True)
        self.assertEqual(HeadlessUI(auto='deny').confirm('x', 'x'), False)

    def test_thinking_window_begin_and_end(self):
        engine = make_engine()
        try:
            engine._ui = _RecordUI()
            engine.provider.chat.return_value = [
                {'type': 'thinking', 'content': 'reasoning'},
                {'type': 'token', 'content': 'Answer'},
                {'type': 'done', 'reason': 'stop'},
            ]
            engine.chat('q')
            kinds = [c[0] for c in engine._ui.calls]
            self.assertEqual(kinds, ['begin', 'thinking', 'end'])
            self.assertEqual(engine._ui.calls[1], ('thinking', 'reasoning'))
            self.assertEqual(engine._ui.calls[2][0], 'end')
            self.assertGreaterEqual(engine._ui.calls[2][1], 0)
        finally:
            engine._tmp.cleanup()

    def test_thinking_window_skipped_without_thinking(self):
        engine = make_engine()
        try:
            engine._ui = _RecordUI()
            engine.provider.chat.return_value = [
                {'type': 'token', 'content': 'Answer'},
                {'type': 'done', 'reason': 'stop'},
            ]
            engine.chat('q')
            self.assertEqual(engine._ui.calls, [])
        finally:
            engine._tmp.cleanup()


class TestEngineModes(unittest.TestCase):

    def setUp(self):
        self.engine = make_engine()
        self.engine.provider.chat.return_value = [
            {'type': 'token', 'content': 'Answer'},
            {'type': 'done', 'reason': 'stop'},
        ]

    def tearDown(self):
        self.engine._tmp.cleanup()

    def test_plan_mode_filters_write_and_exec_from_schema(self):
        self.engine.config.set('mode', 'plan')
        schema = self.engine._init_tooling()
        names = [s['function']['name'] for s in schema]
        self.assertNotIn('write_file', names)
        self.assertNotIn('run_command', names)
        self.assertIn('read_file', names)
        self.assertIn('web_search', names)

    def test_build_mode_schema_unfiltered(self):
        schema = self.engine._init_tooling()
        names = [s['function']['name'] for s in schema]
        self.assertIn('write_file', names)
        self.assertIn('run_command', names)

    def test_plan_mode_instruction_sent_to_provider(self):
        self.engine.config.set('mode', 'plan')
        self.engine.chat('q')
        msgs = self.engine.provider.chat.call_args.args[0]
        self.assertEqual(msgs[0]['role'], 'system')
        self.assertIn('plan mode', msgs[0]['content'])
        self.assertIn('read-only', msgs[0]['content'])

    def test_system_prompt_injected_for_headless(self):
        self.engine.config.set('system_prompt', 'You are a compliance bot.')
        self.engine.chat('q')
        msgs = self.engine.provider.chat.call_args.args[0]
        self.assertEqual(msgs[0]['role'], 'system')
        self.assertIn('compliance bot', msgs[0]['content'])

    def test_mode_recorded_on_assistant_message(self):
        self.engine.config.set('mode', 'plan')
        self.engine.chat('q')
        assistant = [m for m in self.engine.current_session.messages
                     if m['role'] == 'assistant'][0]
        self.assertEqual(assistant['mode'], 'plan')

    def test_mode_recorded_on_tool_call_message(self):
        self.engine.config.set('mode', 'plan')
        self.engine.provider.chat.side_effect = [
            [{'type': 'tool_calls', 'tool_calls': [{
                'id': 'c1', 'type': 'function',
                'function': {'name': 'grep', 'arguments': '{"pattern": "x", "glob": "*.py"}'},
            }]}],
            [{'type': 'token', 'content': 'Final'},
             {'type': 'done', 'reason': 'stop'}],
        ]
        self.engine.chat('q')
        assistant = [m for m in self.engine.current_session.messages
                     if m['role'] == 'assistant' and m.get('tool_calls')][0]
        self.assertEqual(assistant['mode'], 'plan')

    def test_plan_mode_run_tool_refuses_write(self):
        self.engine.config.set('mode', 'plan')
        self.engine._init_tooling()
        out = self.engine._run_tool('write_file', {'path': 'x.txt', 'content': 'x'})
        self.assertIn('disabled by tool policy', out)

    def test_unknown_mode_falls_back_to_build(self):
        self.engine.config.set('mode', 'nosuch')
        schema = self.engine._init_tooling()
        names = [s['function']['name'] for s in schema]
        self.assertIn('write_file', names)


if __name__ == '__main__':
    unittest.main()
