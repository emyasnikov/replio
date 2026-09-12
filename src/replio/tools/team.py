from typing import Callable

_RANK = {'deny': 0, 'ask': 1, 'allow': 2}


def _stage_action(engine, entry) -> str:
    action = (entry.tool_permission or {}).get('delegate', 'allow')
    return action if action in _RANK else 'allow'


def _team_action(engine, args: dict) -> str:
    name = (args or {}).get('name', '')
    team = engine.teams.find(name)
    if team is None or not team.stages:
        return 'allow'
    action = 'allow'
    for stage in team.stages:
        entry = engine.types.find(stage.type)
        if entry is None:
            continue
        stage_action = _stage_action(engine, entry)
        if stage_action == 'deny':
            return 'deny'
        if stage_action == 'ask':
            action = 'ask'
    return action


def _clamped_stages(engine, team) -> list[str]:
    from ..types import resolve_permissions
    out: list[str] = []
    for stage in team.stages:
        entry = engine.types.find(stage.type)
        if entry is None:
            continue
        requested = entry.tool_permission or {}
        granted = resolve_permissions(
            engine._self_permissions(), engine._grant(), requested)
        for key, value in requested.items():
            if isinstance(value, str) and value in _RANK and granted.get(key) != value:
                out.append(stage.type)
                break
    return out


def _format_result(team_name: str, res) -> str:
    if res.status == 'error':
        msgs = '; '.join(e.get('message', '') for e in (res.errors or [])
                         if isinstance(e, dict) and e.get('message'))
        return f'Error: team "{team_name}" failed: {msgs or "unknown error"}'
    content = (res.content or '').strip()
    if content:
        return f'[team {team_name}] {content}'
    return f'[team {team_name}] (no final text; {len(res.stages)} stage(s) ran)'


def _team_footer(engine, res):
    duration = 0.0
    out = 0
    for stage in (res.stages or []):
        duration += float(getattr(stage, 'duration', 0.0) or 0.0)
        usage = getattr(stage, 'usage', None)
        if isinstance(usage, dict):
            comp = usage.get('completion_tokens')
            if isinstance(comp, int) and comp > 0:
                out += comp
    counts = {}
    if out:
        counts['out'] = out
    last_session = ''
    if res.stages:
        last_session = getattr(res.stages[-1], 'session', '') or ''
    note = ' '.join(p for p in (getattr(res, 'status', ''), last_session) if p)
    engine.ui.footer(round(duration, 1), counts, note=note)


def register_team_tool(registry, engine) -> Callable:
    @registry.register(
        name='team',
        description=(
            "Run a named team - an ordered chain of agent-type stages - on a task "
            "and return the final stage's answer. Use it to orchestrate a pipeline "
            "(research > write > reference > edit, or plan > implement > test > "
            "review) in one call instead of delegating each stage yourself."
        ),
        parameters={
            'type': 'object',
            'properties': {
                'name': {
                    'type': 'string',
                    'description': 'Name of the team to run',
                },
                'task': {
                    'type': 'string',
                    'description': 'Task for the team to complete',
                },
                'skills': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'description': 'Skill names to add to every stage for this '
                                   'run, layered over each stage type\'s own '
                                   'skills. Use it to extend the whole team '
                                   'with task, technology, stack, or framework '
                                   'instructions.',
                },
                'warm': {
                    'type': 'boolean',
                    'description': 'Force persistent member sessions for this '
                                   'run, so each stage keeps its context across '
                                   'runs. Default: the team\'s own setting.',
                },
            },
            'required': ['name', 'task'],
        },
        category='delegate',
        permission='delegate',
        key_arg='name',
        short='Run a named team pipeline',
        glyph='↳',
        verb='Team',
        loop=True,
        permission_fn=lambda args: _team_action(engine, args),
    )
    def team(name: str, task: str, skills: list | None = None,
             warm: bool | None = None,
             _config=None, _echo: bool = True) -> str:
        team_obj = engine.teams.find(name)
        if team_obj is None:
            return f'Error: unknown team "{name}"'
        if not team_obj.stages:
            return f'Error: team "{name}" has no stages'
        res = engine.run_team(team_obj, task, skills=skills, warm=warm)
        result = _format_result(name, res)
        clamped = _clamped_stages(engine, team_obj)
        if clamped:
            result += (f' (reduced permissions for: '
                       f'{", ".join(sorted(set(clamped)))})')
        if (_echo and _config is not None and _config.get('delegate_echo', True)
                and not result.startswith('Error')):
            engine.ui.tool_result(result)
            _team_footer(engine, res)
        return result
    return team
