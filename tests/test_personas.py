import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from replio import personas as personas_mod
from replio.personas import Persona, PersonaRegistry
from replio.config import Config

from tests.helpers import make_chat

BUNDLED = Path(personas_mod.__file__).with_name(
    PersonaRegistry.BUNDLED_FILENAME)


class TestPersonaRegistry(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.local = self.base / 'proj' / '.replio' / 'personas.json'

    def tearDown(self):
        self.tmp.cleanup()

    def reg(self, global_dir=None, local_path=None, bundled_path=None):
        if bundled_path is None:
            bundled_path = self.base / 'nobundled' / 'personas.json'
        return PersonaRegistry(global_dir=global_dir or self.base,
                               local_path=local_path or self.local,
                               bundled_path=bundled_path)

    def bundled(self, local_path=None):
        return PersonaRegistry(global_dir=self.base,
                               local_path=local_path or self.local,
                               bundled_path=BUNDLED)

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

    def test_bundled_defaults_loaded(self):
        reg = self.bundled()
        names = reg.names()
        self.assertEqual(len(names), 8)
        for expected in ('researcher', 'writer', 'referencer', 'editor',
                         'planner', 'programmer', 'tester', 'code-reviewer'):
            self.assertIn(expected, names)
        self.assertEqual(reg.origin('researcher'), 'bundled')
        researcher = reg.find('researcher')
        self.assertEqual(researcher.tool_permission['edit'], 'deny')
        self.assertEqual(researcher.tool_permission['web'], 'allow')
        self.assertEqual(reg.find('programmer').tool_permission['bash'], 'allow')
        self.assertEqual(reg.find('editor').tool_permission['edit'], 'deny')

    def test_bundled_overridden_by_global_and_local(self):
        reg = self.bundled()
        reg.put(Persona(name='researcher', system_prompt='global variant'),
                scope='global')
        p = reg.find('researcher')
        self.assertEqual(p.system_prompt, 'global variant')
        self.assertEqual(p.tool_permission['edit'], 'deny')
        self.assertEqual(reg.origin('researcher'), 'merged')
        reg.put(Persona(name='researcher', system_prompt='local variant'),
                scope='local')
        self.assertEqual(reg.find('researcher').system_prompt, 'local variant')

    def test_bundled_restored_after_override_removed(self):
        reg = self.bundled()
        bundled_prompt = reg.find('researcher').system_prompt
        reg.put(Persona(name='researcher', system_prompt='mine'), scope='local')
        self.assertEqual(reg.find('researcher').system_prompt, 'mine')
        self.assertTrue(reg.remove('researcher'))
        p = reg.find('researcher')
        self.assertEqual(p.system_prompt, bundled_prompt)
        self.assertEqual(reg.origin('researcher'), 'bundled')


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

    def test_list_shows_bundled(self):
        out = self._persona()
        self.assertIn('8 personas', out)
        self.assertIn('researcher', out)
        self.assertIn('(bundled)', out)

    def test_new_then_list(self):
        self._persona('new custom')
        out = self._persona()
        self.assertIn('custom', out)

    def test_show(self):
        self._persona('new researcher Web search agent')
        out = self._persona('show researcher')
        self.assertIn('Web search agent', out)

    def test_new_overrides_existing(self):
        self._persona('new x one')
        out = self._persona('new x two')
        self.assertIn('Overrode persona: x', out)
        out = self._persona('show x')
        self.assertIn('two', out)

    def test_remove_local(self):
        self._persona('new x')
        out = self._persona('remove x')
        self.assertIn('Removed persona: x', out)

    def test_remove_bundled_rejected(self):
        out = self._persona('remove researcher')
        self.assertIn('bundled with replio', out)

    def test_override_bundled_then_remove(self):
        self._persona('new researcher local text')
        out = self._persona('show researcher')
        self.assertIn('local text', out)
        out = self._persona('remove researcher')
        self.assertIn('Removed persona: researcher', out)


if __name__ == '__main__':
    unittest.main()
