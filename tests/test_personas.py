import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from replio.personas import Persona, PersonaRegistry
from replio.config import Config

from tests.helpers import make_chat


class TestPersonaRegistry(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.local = self.base / 'proj' / '.replio' / 'personas.json'

    def tearDown(self):
        self.tmp.cleanup()

    def reg(self, global_dir=None, local_path=None):
        return PersonaRegistry(global_dir=global_dir or self.base,
                               local_path=local_path or self.local)

    def test_paths(self):
        reg = self.reg()
        self.assertEqual(reg.global_path,
                         self.base / '.config' / 'replio' / 'personas.json')
        self.assertEqual(reg.local_path, self.local)

    def test_empty(self):
        self.assertEqual(self.reg().all(), [])
        self.assertEqual(self.reg().names(), [])

    def test_put_local_and_find(self):
        reg = self.reg()
        reg.put(Persona(name='researcher', system_prompt='Search the web.'))
        p = reg.find('researcher')
        self.assertIsNotNone(p)
        self.assertEqual(p.system_prompt, 'Search the web.')
        self.assertEqual(reg.origin('researcher'), 'local')

    def test_put_fields_roundtrip(self):
        reg = self.reg()
        reg.put(Persona(name='writer', model='deepseek-r1',
                        skills=['writers'],
                        tool_permission={'delegate': 'ask'}))
        p = reg.find('writer')
        self.assertEqual(p.model, 'deepseek-r1')
        self.assertEqual(p.skills, ['writers'])
        self.assertEqual(p.tool_permission, {'delegate': 'ask'})

    def test_global_and_local_merge_local_wins(self):
        g = PersonaRegistry(global_dir=self.base,
                            local_path=Path(self.tmp.name) / 'g' / 'p.json')
        g.put(Persona(name='x', system_prompt='global prompt', model='m1'),
              scope='global')
        reg = self.reg()
        reg.put(Persona(name='x', system_prompt='local prompt'), scope='local')
        p = reg.find('x')
        self.assertEqual(p.system_prompt, 'local prompt')
        self.assertEqual(p.model, 'm1')
        self.assertEqual(reg.origin('x'), 'merged')

    def test_local_only_does_not_add_to_global(self):
        reg = self.reg()
        reg.put(Persona(name='only-local'), scope='local')
        fresh = PersonaRegistry(global_dir=self.base,
                                local_path=Path(self.tmp.name) / 'z' / 'p.json')
        self.assertIsNone(fresh.find('only-local'))

    def test_remove_local(self):
        reg = self.reg()
        reg.put(Persona(name='x'))
        self.assertTrue(reg.remove('x'))
        self.assertIsNone(reg.find('x'))
        self.assertFalse(reg.remove('x'))

    def test_reload_from_disk(self):
        self.reg().put(Persona(name='x', system_prompt='p'))
        reg2 = self.reg()
        self.assertEqual(reg2.find('x').system_prompt, 'p')

    def test_all_sorted_by_name(self):
        reg = self.reg()
        reg.put(Persona(name='z'))
        reg.put(Persona(name='a'))
        self.assertEqual([p.name for p in reg.all()], ['a', 'z'])
        self.assertEqual(reg.names(), ['a', 'z'])

    def test_default_uses_config_global_dir(self):
        prev = Config.GLOBAL_DIR
        Config.GLOBAL_DIR = self.base
        try:
            reg = PersonaRegistry(local_path=self.local)
            self.assertEqual(reg.global_path,
                             self.base / '.config' / 'replio' / 'personas.json')
        finally:
            Config.GLOBAL_DIR = prev

    def test_bad_json_ignored(self):
        self.local.parent.mkdir(parents=True, exist_ok=True)
        self.local.write_text('{invalid')
        self.assertEqual(self.reg().all(), [])


class TestPersonaCommand(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.chat = make_chat()

    def tearDown(self):
        self.chat._tmp.cleanup()
        self.tmp.cleanup()

    def _persona(self, arg=''):
        with patch('sys.stdout', new=io.StringIO()) as buf:
            self.chat.registry.dispatch('/persona ' + arg)
        return buf.getvalue()

    def test_list_empty(self):
        out = self._persona()
        self.assertIn('no personas configured', out)

    def test_new_then_list(self):
        self._persona('new researcher')
        out = self._persona()
        self.assertIn('researcher', out)

    def test_show(self):
        self._persona('new researcher Web search agent')
        out = self._persona('show researcher')
        self.assertIn('Web search agent', out)

    def test_new_duplicate_rejected(self):
        self._persona('new x')
        out = self._persona('new x')
        self.assertIn('already exists', out)

    def test_remove(self):
        self._persona('new x')
        out = self._persona('remove x')
        self.assertIn('Removed persona: x', out)
        self.assertIn('no personas configured', self._persona())


if __name__ == '__main__':
    unittest.main()
