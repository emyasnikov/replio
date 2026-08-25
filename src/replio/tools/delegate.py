from typing import Callable


def _delegate_action(engine, args: dict) -> str:
    persona = (args or {}).get('persona', '')
    entry = engine.personas.find(persona)
    if entry is None:
        return 'deny'
    action = (entry.tool_permission or {}).get('delegate', 'ask')
    return action if action in ('allow', 'ask', 'deny') else 'ask'


def _format_result(persona: str, res) -> str:
    if res.status == 'error':
        msgs = '; '.join(e.get('message', '') for e in (res.errors or []) if e.get('message'))
        return f'Error: delegated task failed: {msgs or "unknown error"}'
    content = (res.content or '').strip()
    if not content:
        return f'[delegate {persona}] (no content)'
    return f'[delegate {persona}] {content}'


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
    def delegate(persona: str, task: str, _config=None) -> str:
        try:
            res = engine.run_subagent(persona, task)
        except ValueError as e:
            return f'Error: {e}'
        result = _format_result(persona, res)
        if (_config is not None and _config.get('delegate_echo', True)
                and not result.startswith('Error')):
            engine.ui.tool_result(result)
            _sub_footer(engine, res)
        return result
    return delegate