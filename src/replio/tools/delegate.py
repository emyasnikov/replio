from typing import Callable

_WRITE_PREFIXES = ('Created ', 'Overwritten ', 'Appended ')


def _delegate_action(engine, args: dict) -> str:
    persona = (args or {}).get('persona', '')
    entry = engine.personas.find(persona)
    if entry is None:
        return 'deny'
    action = (entry.tool_permission or {}).get('delegate', 'allow')
    return action if action in ('allow', 'ask', 'deny') else 'allow'


def _summarize_session(engine, result) -> str:
    session = engine.sessions.read(result.session) if result.session else None
    if session is None:
        return ''
    tools = [m for m in session.messages if m.get('tool_calls')]
    turns = sum(1 for t in tools for _ in (t.get('tool_calls') or []))
    files: list[str] = []
    last_command = ''
    for m in session.messages:
        if m.get('role') != 'tool':
            continue
        text = (m.get('content') or '').strip()
        if not text:
            continue
        if m.get('tool') in ('file_write', 'write_file', 'write'):
            head = text.splitlines()[0]
            for prefix in _WRITE_PREFIXES:
                if head.startswith(prefix):
                    files.append(head[len(prefix):].split(' (')[0])
                    break
        elif m.get('tool') in ('bash', 'run_command', 'exec'):
            last_command = text.splitlines()[0][:80]
    parts = []
    if turns:
        parts.append(f'{turns} tool calls')
    if files:
        shown = ', '.join(files[:5])
        more = f' (+{len(files) - 5} more)' if len(files) > 5 else ''
        parts.append(f'wrote: {shown}{more}')
    if not parts:
        parts.append('no tool activity recorded')
    summary = '; '.join(parts)
    if last_command:
        summary += f'; last bash: {last_command}'
    if len(summary) > 320:
        summary = summary[:320].rsplit(',', 1)[0] + '...'
    return summary


def _format_result(engine, persona: str, res) -> str:
    if res.status == 'error':
        msgs = '; '.join(e.get('message', '') for e in (res.errors or []) if e.get('message'))
        return f'Error: delegated task failed: {msgs or "unknown error"}'
    content = (res.content or '').strip()
    if content:
        return f'[delegate {persona}] {content}'
    summary = _summarize_session(engine, res)
    if summary:
        return f'[delegate {persona}] (no final text; {summary})'
    return f'[delegate {persona}] (no content)'


def _sub_footer(engine, res):
    counts = {}
    usage = res.usage if isinstance(res.usage, dict) else None
    comp = usage.get('completion_tokens') if usage else None
    if isinstance(comp, int) and comp > 0:
        counts['out'] = comp
    engine.ui.footer(res.duration, counts)


def register_delegate_tool(registry, engine) -> Callable:
    @registry.register(
        name='delegate',
        description=(
            "Run a task with a persona as a sub-agent and return its final answer. "
            "The sub-agent runs in its own session under the persona's system prompt "
            "and permissions. Use it for specialized work (research, writing, review), "
            "then continue from the returned result."
        ),
        parameters={
            'type': 'object',
            'properties': {
                'persona': {
                    'type': 'string',
                    'description': 'Name of the persona to delegate to',
                },
                'task': {
                    'type': 'string',
                    'description': 'Task for the sub-agent to complete',
                },
            },
            'required': ['persona', 'task'],
        },
        category='delegate',
        permission='delegate',
        key_arg='persona',
        short='Run a task with a persona',
        glyph='↳',
        verb='Delegate',
        permission_fn=lambda args: _delegate_action(engine, args),
    )
    def delegate(persona: str, task: str, _config=None, _echo: bool = True) -> str:
        try:
            res = engine.run_subagent(persona, task)
        except ValueError as e:
            return f'Error: {e}'
        result = _format_result(engine, persona, res)
        if (_echo and _config is not None and _config.get('delegate_echo', True)
                and not result.startswith('Error')):
            engine.ui.tool_result(result)
            _sub_footer(engine, res)
        return result
    return delegate