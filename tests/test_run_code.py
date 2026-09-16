import tempfile
import unittest
from pathlib import Path

from replio.runs import RunRegistry
from replio.sessions.manager import (CODE_LEN, Session, SessionManager,
                                     coded_name, name_code, run_code)
from tests.helpers import make_chat


class TestRunCode(unittest.TestCase):

    def test_deterministic_and_short(self):
        code = run_code('ses_20260915_120000', 'assistant')
        self.assertEqual(code, run_code('ses_20260915_120000', 'assistant'))
        self.assertEqual(len(code), CODE_LEN)
        self.assertTrue(all(c in '0123456789abcdefghijklmnopqrstuvwxyz'
                            for c in code))

    def test_different_parts_differ(self):
        self.assertNotEqual(run_code('a'), run_code('b'))

    def test_custom_length(self):
        self.assertEqual(len(run_code('a', length=10)), 10)

    def test_session_stores_code_and_round_trips(self):
        s = Session('ses_20260915_120000_ab12cd', code='ab12cd')
        self.assertEqual(s.code, 'ab12cd')
        restored = Session.from_dict(s.to_dict())
        self.assertEqual(restored.code, 'ab12cd')

    def test_missing_code_loads_empty(self):
        data = Session('legacy').to_dict()
        data.pop('code')
        self.assertEqual(Session.from_dict(data).code, '')

    def test_create_mints_embedded_code(self):
        manager = SessionManager(Path(tempfile.mkdtemp()))
        s = manager.create(role='assistant')
        self.assertTrue(s.name.startswith('ses_'))
        self.assertTrue(s.name.endswith(f'_{s.code}'))
        self.assertEqual(len(s.code), CODE_LEN)

    def test_create_mints_unique_codes(self):
        manager = SessionManager(Path(tempfile.mkdtemp()))
        codes = {manager.create(role='assistant').code for _ in range(20)}
        self.assertEqual(len(codes), 20)

    def test_explicit_name_has_no_code(self):
        manager = SessionManager(Path(tempfile.mkdtemp()))
        s = manager.create('myname')
        self.assertEqual(s.name, 'myname')
        self.assertEqual(s.code, '')

    def test_find_by_code(self):
        manager = SessionManager(Path(tempfile.mkdtemp()))
        s = manager.create(role='assistant')
        manager.save(s)
        found = manager.find_by_code(s.code)
        self.assertIsNotNone(found)
        self.assertEqual(found.name, s.name)

    def test_name_code_parses_coded_names(self):
        self.assertEqual(name_code('ses_20260915_120000_ab12cd'), 'ab12cd')
        self.assertEqual(name_code('job_20260915_120000_ab12cd'), 'ab12cd')
        self.assertEqual(name_code('sub_20260915_120000_ab12cd'), 'ab12cd')

    def test_name_code_ignores_uncoded_names(self):
        self.assertEqual(name_code(''), '')
        self.assertEqual(name_code('myname'), '')
        self.assertEqual(name_code('agent_writer'), '')
        self.assertEqual(name_code('sub_thesis__writer'), '')
        self.assertEqual(name_code('ses_20260915_120000_slug'), '')

    def test_coded_name_round_trips_code(self):
        name = coded_name('ses', 'assistant')
        code = name_code(name)
        self.assertEqual(len(code), CODE_LEN)
        self.assertTrue(name.endswith(f'_{code}'))

    def test_find_by_code_normalizes_and_misses(self):
        manager = SessionManager(Path(tempfile.mkdtemp()))
        s = manager.create(role='assistant')
        manager.save(s)
        self.assertIsNotNone(manager.find_by_code(s.code.upper()))
        self.assertIsNone(manager.find_by_code('zzzzzz'))
        self.assertIsNone(manager.find_by_code(''))


class TestRunRegistryCode(unittest.TestCase):

    def test_start_stores_code(self):
        reg = RunRegistry()
        run = reg.start(role='assistant', session='ses_x', code='ab12cd')
        self.assertEqual(run.code, 'ab12cd')

    def test_find_by_code(self):
        reg = RunRegistry()
        reg.start(role='assistant', session='ses_x', code='ab12cd')
        reg.start(role='writer', session='ses_y', code='cd34ef')
        self.assertEqual(reg.find_by_code('CD34EF').role, 'writer')
        self.assertIsNone(reg.find_by_code('nope'))
        self.assertIsNone(reg.find_by_code(''))


class TestEngineCode(unittest.TestCase):

    def setUp(self):
        self.chat = make_chat()

    def tearDown(self):
        self.chat._tmp.cleanup()

    def test_run_mirrors_session_code(self):
        self.assertEqual(self.chat.current_run.code,
                         self.chat.current_session.code)

    def test_load_or_create_syncs_run_code(self):
        self.chat.load_or_create_session('foo')
        self.assertEqual(self.chat.current_session.code, '')
        self.assertEqual(self.chat.current_run.code, '')
        self.assertEqual(self.chat.current_run.session, 'foo')

    def test_load_or_create_auto_syncs_run_code(self):
        self.chat.load_or_create_session(None)
        self.assertEqual(self.chat.current_run.code,
                         self.chat.current_session.code)
        self.assertTrue(self.chat.current_session.code)

    def test_turns_do_not_change_code(self):
        s = self.chat.sessions.create(role='assistant')
        code = s.code
        self.chat.sessions.save(s)
        s.add_user('hi')
        s.add_text('yo')
        s.end_turn('ok')
        self.chat.sessions.save(s)
        self.assertEqual(s.code, code)
        found = self.chat.sessions.find_by_code(code)
        self.assertIsNotNone(found)
        self.assertEqual(len(found.turns), 1)


if __name__ == '__main__':
    unittest.main()
