from __future__ import annotations

import re

from .manager import Session


def render_session(session: Session) -> str:
    lines = [
        f'# Session: {session.name}',
        '',
        f'- Created: {session.created_at}',
        f'- Updated: {session.updated_at}',
        f'- Messages: {len(session.messages)}',
        '',
        '---',
        '',
    ]
    for msg in session.messages:
        parts = _render_message(msg)
        if not parts:
            continue
        lines.extend(parts)
        lines.append('')
    if session.errors:
        lines.extend(_render_errors(session.errors))
        lines.append('')
    return '\n'.join(lines).rstrip() + '\n'


def _render_message(msg: dict) -> list[str]:
    role = msg.get('role', '?')
    ts = msg.get('timestamp', '')
    if role == 'user':
        return [
            f'### User - {ts}',
            '',
            msg.get('content', ''),
        ]
    if role == 'assistant':
        return _render_assistant(msg, ts)
    if role == 'tool':
        return _render_tool(msg, ts)
    if role == 'command':
        return _render_command(msg, ts)
    if role == 'system':
        return [
            f'### System - {ts}',
            '',
            *_blockquote(str(msg.get('content', ''))),
        ]
    return []


def _render_assistant(msg: dict, ts: str) -> list[str]:
    lines = [f'### Assistant - {ts}', '']
    meta_parts: list[str] = []
    model = msg.get('model')
    provider = msg.get('provider')
    if provider or model:
        meta_parts.append(':'.join(p for p in (provider, model) if p))
    duration = msg.get('duration')
    if duration is not None:
        meta_parts.append(f'{duration}s')
    if meta_parts:
        lines.append('*' + ' · '.join(meta_parts) + '*')
        lines.append('')
    thinking = msg.get('thinking')
    if thinking:
        lines.append('> _Thinking:_')
        lines.extend(_blockquote(thinking))
        lines.append('')
    content = msg.get('content')
    if content:
        lines.append(content)
    for tc in msg.get('tool_calls') or []:
        fn = tc.get('function', {})
        name = fn.get('name', '?')
        args = fn.get('arguments', '')
        lines.extend([
            '',
            f'**Tool call: {name}**',
            '',
            _fence(args, 'json'),
        ])
    return lines


def _render_tool(msg: dict, ts: str) -> list[str]:
    name = msg.get('tool', '?')
    lines = [f'### Tool: {name} - {ts}', '']
    analysis = msg.get('analysis')
    if analysis:
        lines.append(f'> _Analysis: {analysis}_')
        lines.append('')
    lines.append(_fence(str(msg.get('content') or ''), 'text'))
    return lines


def _render_command(msg: dict, ts: str) -> list[str]:
    lines = [f'### Command - {ts}', '']
    content = msg.get('content')
    if content:
        lines.append(f'`{content}`')
    result = msg.get('result')
    if result:
        lines.extend([
            '',
            'Earlier conversation (summarized):',
            '',
            *_blockquote(result),
        ])
    compact_from = msg.get('compact_from')
    if compact_from is not None:
        lines.append('')
        lines.append(f'Provider context trimmed at message index {compact_from}.')
    return lines


def _render_errors(errors: list[dict]) -> list[str]:
    lines = ['## Errors', '']
    for e in errors:
        code = e.get('code', '')
        message = e.get('message', '')
        ts = e.get('timestamp', '')
        lines.append(f'- `{code}` {message} at {ts}')
    return lines


def _blockquote(text: str) -> list[str]:
    return [f'> {line}' if line else '>' for line in text.splitlines()]


def _fence(content: str, lang: str = '') -> str:
    ticks = '```'
    while ticks in content:
        ticks += '`'
    return f'{ticks}{lang}\n{content}\n{ticks}'