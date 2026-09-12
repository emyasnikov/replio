import io
import json
import unittest
from unittest.mock import patch

from replio.engine import TeamRunResult
from replio.teams import Team, TeamStage
from replio.types import AgentType

from tests.helpers import make_chat


class TestWarmSessions(unittest.TestCase):

    def setUp(self):
        self.chat = make_chat()
        self.sessions_dir = self.chat.config.local_path.parent / 'sessions'
        for name in ('researcher', 'writer'):
            self.chat.types.put(
                AgentType(name=name, system_prompt=f'You are the {name}.'),
                scope='local')

    def tearDown(self):
        self.chat._tmp.cleanup()

    def _result(self, content):
        return ({'type': 'token', 'content': content},
                {'type': 'done', 'reason': 'stop'})

    def _session(self, name):
        return json.loads((self.sessions_dir / f'{name}.json').read_text())

    def test_warm_session_name(self):
        from replio.engine import _warm_session_name
        self.assertEqual(_warm_session_name('thesis/writer'),
                         'sub_thesiswriter')
        self.assertEqual(_warm_session_name('a b'), 'sub_ab')

    def test_delegate_reuses_keyed_session(self):
        self.chat.provider.chat.side_effect = [
            self._result('first'), self._result('second'),
        ]
        r1 = self.chat.run_subagent('writer', 'task one',
                                    session_key='warm-writer')
        r2 = self.chat.run_subagent('writer', 'task two',
                                    session_key='warm-writer')
        self.assertEqual(r1.session, 'sub_warm-writer')
        self.assertEqual(r2.session, 'sub_warm-writer')
        users = [m['content'] for m in self._session(r1.session)['messages']
                 if m['role'] == 'user']
        self.assertEqual(users, ['task one', 'task two'])

    def test_default_sessions_are_fresh(self):
        self.chat.provider.chat.side_effect = [
            self._result('a'), self._result('b'),
        ]
        r1 = self.chat.run_subagent('writer', 't1')
        r2 = self.chat.run_subagent('writer', 't2')
        self.assertNotEqual(r1.session, r2.session)
        self.assertTrue(r1.session.startswith('sub_'))

    def test_team_warm_sessions_reuse(self):
        team = Team(name='doc', warm_sessions=True, stages=[
            TeamStage(type='researcher'), TeamStage(type='writer')])
        self.chat.provider.chat.side_effect = [
            self._result('r1'), self._result('w1'),
            self._result('r2'), self._result('w2'),
        ]
        res1 = self.chat.run_team(team, 'task one')
        res2 = self.chat.run_team(team, 'task two')
        names1 = [s.session for s in res1.stages]
        names2 = [s.session for s in res2.stages]
        self.assertEqual(names1, ['sub_doc__researcher', 'sub_doc__writer'])
        self.assertEqual(names1, names2)
        users = [m['content'] for m in self._session('sub_doc__writer')['messages']
                 if m['role'] == 'user']
        self.assertEqual(len(users), 2)

    def test_team_cold_sessions_without_warm(self):
        team = Team(name='cold', stages=[TeamStage(type='writer')])
        self.chat.provider.chat.side_effect = [
            self._result('a'), self._result('b'),
        ]
        res1 = self.chat.run_team(team, 'one')
        res2 = self.chat.run_team(team, 'two')
        self.assertNotEqual(res1.stages[0].session, res2.stages[0].session)

    def test_stage_session_key_overrides(self):
        team = Team(name='doc', stages=[
            TeamStage(type='writer', session_key='my-writer')])
        self.chat.provider.chat.side_effect = [self._result('a')]
        res = self.chat.run_team(team, 'task')
        self.assertEqual(res.stages[0].session, 'sub_my-writer')

    def test_warm_override_forces_warm(self):
        team = Team(name='doc', stages=[TeamStage(type='writer')])
        self.chat.provider.chat.side_effect = [
            self._result('a'), self._result('b'),
        ]
        res1 = self.chat.run_team(team, 'one', warm=True)
        res2 = self.chat.run_team(team, 'two', warm=True)
        self.assertEqual(res1.stages[0].session, 'sub_doc__writer')
        self.assertEqual(res1.stages[0].session, res2.stages[0].session)

    def test_delegate_tool_forwards_session_key(self):
        from types import SimpleNamespace
        self.chat.types.put(
            AgentType(name='dev', system_prompt='Dev',
                      tool_permission={'delegate': 'allow'}), scope='local')
        with patch.object(self.chat, 'run_subagent', return_value=SimpleNamespace(
                status='ok', content='done', errors=[], session='sub_x',
                duration=0.0, usage=None)) as run:
            with patch('sys.stdout', new=io.StringIO()):
                self.chat._init_tooling()
                self.chat._tool_registry.execute(
                    'delegate', {'type': 'dev', 'task': 't',
                                 'session_key': 'warm-dev'})
        self.assertEqual(run.call_args.kwargs.get('session_key'), 'warm-dev')

    def test_team_tool_forwards_warm(self):
        with patch.object(self.chat, 'run_team',
                          return_value=TeamRunResult(name='writing',
                                                     status='ok')) as run:
            with patch('sys.stdout', new=io.StringIO()):
                self.chat._init_tooling()
                self.chat._tool_registry.execute(
                    'team', {'name': 'writing', 'task': 't', 'warm': True})
        self.assertEqual(run.call_args.kwargs.get('warm'), True)

    def test_catalog_saves_warm_team(self):
        self.chat._init_tooling()
        self.chat._tool_registry.execute('catalog', {
            'action': 'save', 'kind': 'team', 'name': 'warm',
            'warm_sessions': True,
            'stages': [{'type': 'writer', 'session_key': 'w'}]})
        team = self.chat.teams.find('warm')
        self.assertTrue(team.warm_sessions)
        self.assertEqual(team.stages[0].session_key, 'w')

    def test_team_fields_roundtrip(self):
        from replio.teams import TeamRegistry
        import tempfile
        from pathlib import Path
        tmp = tempfile.TemporaryDirectory()
        try:
            reg = TeamRegistry(
                global_dir=Path(tmp.name),
                local_path=Path(tmp.name) / '.replio' / 'teams.json',
                bundled_path=Path(tmp.name) / 'none.json')
            reg.put(Team(name='x', warm_sessions=True, stages=[
                TeamStage(type='w', session_key='k')]))
            fresh = TeamRegistry(
                global_dir=Path(tmp.name),
                local_path=Path(tmp.name) / '.replio' / 'teams.json',
                bundled_path=Path(tmp.name) / 'none.json')
            team = fresh.find('x')
            self.assertTrue(team.warm_sessions)
            self.assertEqual(team.stages[0].session_key, 'k')
        finally:
            tmp.cleanup()


if __name__ == '__main__':
    unittest.main()
