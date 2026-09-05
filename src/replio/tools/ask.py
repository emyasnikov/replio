from typing import Callable


_ASK_SYSTEM = (
    'You are the lead agent coordinating delegated agents. A sub-agent asks you '
    'for a decision or permission. Answer concisely with just the decision, and '
    'add a one-line reason only if it helps. Do not ask questions back; commit '
    'to the decision the sub-agent needs.'
)

_NO_ANSWER = ('[cancelled] No answer given - decide autonomously or return the '
              'question as an open item')
_NO_ONE = ('Error: ask has no one to answer (no lead agent and no interactive '
           'terminal) - decide autonomously or return the question as an open item')


def _task_preview(engine) -> str:
    for m in engine.current_session.messages:
        if m.get('role') == 'user' and m.get('content'):
            text = str(m['content']).strip().replace('\n', ' ')
            return text[:500]
    return ''


def _lead_answer(engine, question: str, context: str, options) -> str | None:
    lead = getattr(engine, '_lead', None)
    if lead is None:
        return None
    parts = [f'Question: {question}']
    if context:
        parts.append(f'Context: {context}')
    if options:
        parts.append('Options: ' + ' / '.join(options))
    task = _task_preview(engine)
    if task:
        parts.append(f'Delegated task: {task}')
    try:
        result = lead.provider.chat_nonstreaming(
            [
                {'role': 'system', 'content': _ASK_SYSTEM},
                {'role': 'user', 'content': '\n'.join(parts)},
            ],
            tools=None,
        )
    except Exception:
        return None
    content = result.get('content') if isinstance(result, dict) else None
    if not isinstance(content, str):
        return None
    content = content.strip()
    return content or None


def register_ask_tool(registry, engine) -> Callable:
    @registry.register(
        name='ask',
        description=(
            "Ask a question and pause until it is answered, to get a decision or "
            "permission mid-run instead of leaving it open. With target='human' "
            "the operator answers at the terminal. With target='lead' the agent "
            "type or engine that delegated this run decides. Use it when a choice "
            "cannot be resolved from the task alone, then continue from the answer."
        ),
        parameters={
            'type': 'object',
            'properties': {
                'question': {
                    'type': 'string',
                    'description': 'The decision or permission request. Frame it so '
                                   'the answerer can resolve it from the question and '
                                   'context alone.',
                },
                'context': {
                    'type': 'string',
                    'description': 'Brief context the answerer needs that is not obvious '
                                   'from the question alone (current state, what was '
                                   'tried, the options under consideration).',
                },
                'options': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'description': 'Suggested answers. The answerer picks one or gives '
                                   'their own.',
                },
                'target': {
                    'type': 'string',
                    'enum': ['human', 'lead'],
                    'description': "'human' asks the operator at the terminal (or the "
                                   "lead agent when headless). 'lead' asks the agent "
                                   "type or engine that delegated this run to decide.",
                },
            },
            'required': ['question'],
        },
        category='ask',
        permission='ask',
        key_arg='question',
        short='Ask the human or the lead agent for a decision',
    )
    def ask(question: str, context: str = '', options: list | None = None,
            target: str = 'human', _config=None) -> str:
        ui = getattr(engine, '_ask_ui', None)
        lead = getattr(engine, '_lead', None)
        if target == 'lead':
            if lead is not None:
                answer = _lead_answer(engine, question, context or '', options or [])
                if answer is not None:
                    return answer
            if ui is not None:
                answer = ui.ask(question, context=context or '',
                                options=options or [],
                                origin=engine.current_session.name)
                return answer or _NO_ANSWER
            return _NO_ONE
        if ui is not None:
            answer = ui.ask(question, context=context or '',
                            options=options or [],
                            origin=engine.current_session.name)
            return answer or _NO_ANSWER
        if lead is not None:
            answer = _lead_answer(engine, question, context or '', options or [])
            if answer is not None:
                return answer
        return _NO_ONE
    return ask
