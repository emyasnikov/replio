from __future__ import annotations

import json
from datetime import datetime

from .manager import Session

SUMMARY_PROMPT_CHARS = 80
THOUGHTS_CHARS = 100
DIM = '\033[90m'
RESET = '\033[0m'


def turn_summary(turn: dict, thoughts: bool | str = False) -> str:
    lines = [_turn_line(turn)]
    if thoughts:
        lines.extend(_thought_lines(turn, full=(thoughts == 'all')))
    return '\n'.join(lines)


def render_session(session: Session) -> str:
    lines = [
        f'# Session: {session.name}',
        '',
        f'- Created: {session.created_at}',
        f'- Updated: {session.updated_at}',
        f'- Turns: {len(session.turns)}',
        '',
        '---',
        '',
    ]
    for turn in session.turns:
        for part in turn.get('parts') or []:
            block = _render_part(part, turn)
            if not block:
                continue
            lines.extend(block)
            lines.append('')
    if session.errors:
        lines.extend(_render_errors(session.errors))
        lines.append('')
    return '\n'.join(lines).rstrip() + '\n'


def _render_part(part: dict, turn: dict) -> list[str]:
    kind = part.get('type')
    ts = part.get('timestamp', '')
    if kind == 'user':
        return [f'### User - {ts}', '', str(part.get('text') or '')]
    if kind == 'text':
        return _render_text(part, turn, ts)
    if kind == 'thinking':
        return [
            f'### Thinking - {ts}',
            '',
            *_blockquote(str(part.get('text') or '')),
        ]
    if kind == 'tool':
        return _render_tool(part, ts)
    if kind == 'command':
        return _render_command(part, ts)
    if kind == 'system':
        return [
            f'### System - {ts}',
            '',
            *_blockquote(str(part.get('text') or '')),
        ]
    return []


def _render_text(part: dict, turn: dict, ts: str) -> list[str]:
    lines = [f'### Assistant - {ts}', '']
    meta_parts: list[str] = []
    provider = turn.get('provider')
    model = turn.get('model')
    if provider or model:
        meta_parts.append(':'.join(p for p in (provider, model) if p))
    duration = _duration(turn)
    if duration is not None:
        meta_parts.append(f'{duration}s')
    if meta_parts:
        lines.append('*' + ' · '.join(meta_parts) + '*')
        lines.append('')
    content = part.get('text')
    if content:
        lines.append(str(content))
    return lines


def _render_tool(part: dict, ts: str) -> list[str]:
    name = part.get('name', '?')
    lines = [f'### Tool: {name} - {ts}', '']
    if part.get('input') is not None:
        lines.extend([
            f'**Tool call: {name}**',
            '',
            _fence(json.dumps(part['input']), 'json'),
            '',
        ])
    analysis = part.get('analysis')
    if analysis:
        lines.append(f'> _Analysis: {analysis}_')
        lines.append('')
    lines.append(_fence(str(part.get('output') or ''), 'text'))
    return lines


def _render_command(part: dict, ts: str) -> list[str]:
    lines = [f'### Command - {ts}', '']
    command = part.get('text')
    if command:
        lines.append(f'`{command}`')
    summary = part.get('summary')
    if summary:
        lines.extend([
            '',
            'Earlier conversation (summarized):',
            '',
            *_blockquote(str(summary)),
        ])
    compact_from = part.get('compact_from')
    if compact_from is not None:
        lines.append('')
        lines.append(f'Provider context trimmed at turn {compact_from}.')
    return lines


def _turn_line(turn: dict) -> str:
    index = turn.get('index', 0)
    status = turn.get('status', '')
    duration = _duration(turn)
    duration_str = f'{duration}s' if duration is not None else '-'
    count = _turn_tool_count(turn)
    tools = f'{count} tool' + ('' if count == 1 else 's')
    prompt = _clip(_turn_prompt(turn), SUMMARY_PROMPT_CHARS)
    return f'#{index}  [{status}]  {duration_str}  {tools}  {prompt}'


def _turn_prompt(turn: dict) -> str:
    parts = turn.get('parts') or []
    for kind in ('user', 'command'):
        for part in parts:
            if part.get('type') == kind:
                text = _first_line(str(part.get('text') or ''))
                if text:
                    return text
    return '(no prompt)'


def _turn_tool_count(turn: dict) -> int:
    return sum(1 for p in (turn.get('parts') or [])
               if p.get('type') == 'tool')


def _thought_lines(turn: dict, full: bool) -> list[str]:
    lines: list[str] = []
    for part in turn.get('parts') or []:
        if part.get('type') != 'thinking':
            continue
        text = str(part.get('text') or '')
        if not text.strip():
            continue
        if full:
            body = text.splitlines()
        else:
            body = [_clip(_first_line(text), THOUGHTS_CHARS)]
        for line in body:
            lines.append(f'{DIM}    {line}{RESET}')
    return lines


def _first_line(text: str) -> str:
    for line in text.splitlines():
        if line.strip():
            return line.strip()
    return ''


def _clip(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + '...'


def _duration(turn: dict) -> float | None:
    start = turn.get('started_at')
    end = turn.get('ended_at')
    if not start or not end:
        return None
    try:
        delta = datetime.fromisoformat(end) - datetime.fromisoformat(start)
    except ValueError:
        return None
    return round(delta.total_seconds(), 1)


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
