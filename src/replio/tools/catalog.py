import json
from typing import Callable

from ..skills import Skill
from ..teams import Team
from ..types import AgentType

_TYPE_FIELDS = ('system_prompt', 'model', 'skills', 'tags',
                'tool_permission', 'grant_permission', 'ask_policy')


def _type_line(engine, agent_type) -> str:
    parts = []
    if agent_type.model:
        parts.append(f'model={agent_type.model}')
    if agent_type.tags:
        parts.append(f'tags={",".join(agent_type.tags)}')
    if agent_type.skills:
        parts.append(f'skills={",".join(agent_type.skills)}')
    detail = ' ' + ' '.join(parts) if parts else ''
    return f'- {agent_type.name}{detail} ({engine.types.origin(agent_type.name)})'


def _team_line(engine, team) -> str:
    chain = ' > '.join(stage.type for stage in team.stages) or '(no stages)'
    tags = f' tags={",".join(team.tags)}' if team.tags else ''
    return (f'- {team.name}{tags} ({engine.teams.origin(team.name)}): {chain}')


def _skill_line(engine, skill) -> str:
    desc = (skill.description or '').strip().splitlines()
    suffix = f': {desc[0][:80]}' if desc else ''
    return f'- {skill.name} ({engine.skills.origin(skill.name)}){suffix}'


def _show_type(engine, name: str) -> str:
    agent_type = engine.types.find(name)
    if agent_type is None:
        return f'Error: unknown agent type "{name}"'
    lines = [f'{agent_type.name} ({engine.types.origin(name)})']
    lines.append(f'system_prompt: {agent_type.system_prompt or "(empty)"}')
    if agent_type.model:
        lines.append(f'model: {agent_type.model}')
    if agent_type.skills:
        lines.append(f'skills: {", ".join(agent_type.skills)}')
    if agent_type.tags:
        lines.append(f'tags: {", ".join(agent_type.tags)}')
    for key in ('tool_permission', 'grant_permission', 'ask_policy'):
        value = getattr(agent_type, key)
        if value:
            lines.append(f'{key}: {json.dumps(value)}')
    return '\n'.join(lines)


def _show_team(engine, name: str) -> str:
    team = engine.teams.find(name)
    if team is None:
        return f'Error: unknown team "{name}"'
    lines = [f'{team.name} ({engine.teams.origin(name)})']
    if team.description:
        lines.append(f'description: {team.description}')
    if team.tags:
        lines.append(f'tags: {", ".join(team.tags)}')
    if not team.stages:
        lines.append('stages: (none)')
    for i, stage in enumerate(team.stages, 1):
        parts = [f'{i}. {stage.type}']
        if stage.mode:
            parts.append(f'mode={stage.mode}')
        lines.append(' '.join(parts))
        if stage.skills:
            lines.append(f'   skills: {", ".join(stage.skills)}')
        if stage.task_hint:
            lines.append(f'   task_hint: {stage.task_hint}')
        if stage.handoff_note:
            lines.append(f'   handoff_note: {stage.handoff_note}')
    return '\n'.join(lines)


def _show_skill(engine, name: str) -> str:
    skill = engine.skills.find(name)
    if skill is None:
        return f'Error: unknown skill "{name}"'
    return f'{skill.name} ({engine.skills.origin(name)})\n{skill.content}'


def _save_type(engine, name: str, values: dict) -> str:
    data = {'name': name}
    for field in _TYPE_FIELDS:
        if values.get(field) is not None:
            data[field] = values[field]
    engine.types.put(AgentType.from_dict(data), scope='local')
    return f'Saved agent type: {name} (local)'


def _save_team(engine, name: str, values: dict) -> str:
    data = {'name': name}
    for field in ('description', 'tags', 'stages', 'warm_sessions', 'loop'):
        if values.get(field) is not None:
            data[field] = values[field]
    engine.teams.put(Team.from_dict(data), scope='local')
    return f'Saved team: {name} (local)'


def _save_skill(engine, name: str, values: dict) -> str:
    skill = Skill(name=name,
                  content=str(values.get('content') or ''),
                  description=str(values.get('description') or ''),
                  tags=list(values.get('tags') or []))
    engine.skills.put(skill, scope='local')
    return f'Saved skill: {name} (local)'


def register_catalog_tool(registry, engine) -> Callable:
    @registry.register(
        name='catalog',
        description=(
            "Manage the agent catalog: agent types, teams, and skills. Use it to "
            "compose a team for a task, create the specialist types and skills it "
            "needs, inspect what exists, or remove local entries. Saving writes to "
            "the project catalog (.replio/) and reloads it, so a new type, team, "
            "or skill is usable in the same run. A team stage's `type` must name an "
            "agent type and its `skills` extend that type for the stage."
        ),
        parameters={
            'type': 'object',
            'properties': {
                'action': {
                    'type': 'string',
                    'enum': ['list', 'show', 'save', 'remove', 'reload'],
                    'description': "list/show/save/remove a kind, or reload the "
                                   "catalog from disk.",
                },
                'kind': {
                    'type': 'string',
                    'enum': ['type', 'team', 'skill'],
                    'description': 'Which catalog to act on.',
                },
                'name': {
                    'type': 'string',
                    'description': 'Entry name for show/save/remove.',
                },
                'system_prompt': {
                    'type': 'string',
                    'description': "Agent type: the role's system prompt.",
                },
                'model': {
                    'type': 'string',
                    'description': 'Agent type: optional model override.',
                },
                'skills': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'description': "Agent type: standing skill names. For a team "
                                   "stage use the stage's own skills field.",
                },
                'tags': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'description': 'Agent type, team, or skill: grouping tags.',
                },
                'tool_permission': {
                    'type': 'object',
                    'description': 'Agent type: per-category permission overrides.',
                },
                'grant_permission': {
                    'type': 'object',
                    'description': 'Agent type: delegation ceiling for sub-agents.',
                },
                'ask_policy': {
                    'type': 'object',
                    'description': 'Agent type: ask routing by kind.',
                },
                'content': {
                    'type': 'string',
                    'description': 'Skill: the markdown instructions.',
                },
                'description': {
                    'type': 'string',
                    'description': 'Team or skill: a short description.',
                },
                'stages': {
                    'type': 'array',
                    'description': 'Team: ordered stages.',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'type': {'type': 'string'},
                            'mode': {'type': 'string'},
                            'task_hint': {'type': 'string'},
                            'handoff_note': {'type': 'string'},
                            'skills': {'type': 'array',
                                       'items': {'type': 'string'}},
                            'session_key': {'type': 'string'},
                        },
                        'required': ['type'],
                    },
                },
                'warm_sessions': {
                    'type': 'boolean',
                    'description': 'Team: keep each stage\'s member session '
                                   'across runs so a role reuses its context.',
                },
                'loop': {
                    'type': 'object',
                    'description': 'Team: generate > check > correct loop. '
                                   'Properties: from (stage type), until '
                                   '(stage type), max_iterations, verdict '
                                   '(marker, default "VERDICT:").',
                    'properties': {
                        'from': {'type': 'string'},
                        'until': {'type': 'string'},
                        'max_iterations': {'type': 'integer'},
                        'verdict': {'type': 'string'},
                    },
                },
            },
            'required': ['action'],
        },
        category='catalog',
        permission='catalog',
        key_arg='name',
        short='Manage agent types, teams, and skills',
        glyph='+',
        verb='Catalog',
    )
    def catalog(action: str, kind: str = '', name: str = '',
                system_prompt: str | None = None, model: str | None = None,
                skills: list | None = None, tags: list | None = None,
                tool_permission: dict | None = None,
                grant_permission: dict | None = None,
                ask_policy: dict | None = None, content: str | None = None,
                description: str | None = None,
                stages: list | None = None,
                warm_sessions: bool | None = None,
                loop: dict | None = None) -> str:
        if action == 'reload':
            reloaded = engine.touch_catalogs()
            return f'Reloaded catalogs: {", ".join(reloaded) or "(none loaded)"}'
        if action not in ('list', 'show', 'save', 'remove'):
            return 'Error: action must be list, show, save, remove, or reload'
        if kind not in ('type', 'team', 'skill'):
            return 'Error: kind must be type, team, or skill'
        if action == 'list':
            if kind == 'type':
                return '\n'.join(_type_line(engine, t) for t in engine.types.all())
            if kind == 'team':
                return '\n'.join(_team_line(engine, t) for t in engine.teams.all())
            return '\n'.join(_skill_line(engine, s) for s in engine.skills.all())
        if not name:
            return f'Error: name is required to {action} a {kind}'
        if action == 'show':
            if kind == 'type':
                return _show_type(engine, name)
            if kind == 'team':
                return _show_team(engine, name)
            return _show_skill(engine, name)
        if action == 'remove':
            if kind == 'type':
                registry = engine.types
            elif kind == 'team':
                registry = engine.teams
            else:
                registry = engine.skills
            if registry.remove(name):
                engine.touch_catalogs()
                return f'Removed {kind}: {name} (local)'
            if kind != 'skill' and registry.is_bundled(name):
                return (f'Error: {kind} "{name}" is bundled - override it with '
                        f'save instead of remove')
            if registry.find(name) is not None:
                return (f'Error: {kind} "{name}" is not local - override it with '
                        f'save instead of remove')
            return f'Error: no local {kind} to remove: {name}'
        values = {'system_prompt': system_prompt, 'model': model,
                  'skills': skills, 'tags': tags,
                  'tool_permission': tool_permission,
                  'grant_permission': grant_permission,
                  'ask_policy': ask_policy, 'content': content,
                  'description': description, 'stages': stages,
                  'warm_sessions': warm_sessions, 'loop': loop}
        if kind == 'type':
            result = _save_type(engine, name, values)
        elif kind == 'team':
            result = _save_team(engine, name, values)
        else:
            result = _save_skill(engine, name, values)
        engine.touch_catalogs()
        return result
    return catalog
