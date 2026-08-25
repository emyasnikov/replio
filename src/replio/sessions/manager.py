import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


class Session:
    def __init__(self, name: str, messages: list | None = None,
                 errors: list | None = None,
                 permissions: list | None = None,
                 created_at: str | None = None,
                 updated_at: str | None = None,
                 parent_id: str = '',
                 sub_sessions: list | None = None):
        now = datetime.now(timezone.utc).isoformat(timespec='seconds')
        self.name = name
        self.messages = messages or []
        self.errors = errors or []
        self.permissions = permissions or []
        self.created_at = created_at or now
        self.updated_at = updated_at or now
        self.parent_id = parent_id or ''
        self.sub_sessions = sub_sessions or []

    def _touch(self):
        self.updated_at = datetime.now(timezone.utc).isoformat(timespec='seconds')

    def _next_id(self) -> str:
        return f'msg_{uuid.uuid4().hex[:16]}'

    def add_message(self, role: str, content: str, **kwargs):
        msg = {'role': role, 'content': content}
        msg['timestamp'] = kwargs.pop(
            'timestamp', datetime.now(timezone.utc).isoformat(timespec='seconds')
        )
        msg['id'] = kwargs.pop('id', self._next_id())
        msg.update(kwargs)
        self.messages.append(msg)
        self._touch()

    def add_error(self, code, message: str, timestamp: str | None = None):
        ts = timestamp or datetime.now(timezone.utc).isoformat(timespec='seconds')
        self.errors.append({'code': code, 'message': message, 'timestamp': ts})
        self._touch()

    def add_permission(self, tool: str, action: str, decision: str,
                       path: str | None = None, timestamp: str | None = None):
        ts = timestamp or datetime.now(timezone.utc).isoformat(timespec='seconds')
        entry = {'tool': tool, 'action': action, 'decision': decision,
                 'timestamp': ts}
        if path is not None:
            entry['path'] = path
        self.permissions.append(entry)
        self._touch()

    def to_dict(self, tool_max_chars: int = 0, noise_tools: list[str] | None = None):
        noise_tools = set(noise_tools or [])
        messages = []
        for m in self.messages:
            m = m.copy() if tool_max_chars > 0 or noise_tools else m
            role = m.get('role')
            content = m.get('content')
            if role == 'tool' and isinstance(content, str):
                if m.get('tool') in noise_tools:
                    m['content'] = (
                        f'[{m["tool"]} result excluded from log; see tool call above for parameters]')
                elif tool_max_chars > 0 and len(content) > tool_max_chars:
                    m['content'] = content[:tool_max_chars] + (
                        f'… (truncated from {len(content)} chars)')
            messages.append(m)
        return {
            'name': self.name,
            'messages': messages,
            'errors': self.errors,
            'permissions': self.permissions,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'parent_id': self.parent_id,
            'sub_sessions': self.sub_sessions,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            data['name'],
            data.get('messages', []),
            data.get('errors', []),
            data.get('permissions', []),
            data.get('created_at'),
            data.get('updated_at'),
            data.get('parent_id', ''),
            data.get('sub_sessions', []),
        )


class SessionManager:
    def __init__(self, sessions_dir: Path):
        self.sessions_dir = sessions_dir
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.current: Session | None = None

    def create(self, name: str | None = None) -> Session:
        if not name:
            name = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.current = Session(name)
        return self.current

    def load(self, name: str) -> Session | None:
        s = self.read(name)
        if s is not None:
            self.current = s
        return s

    def read(self, name: str) -> Session | None:
        path = self.sessions_dir / f'{name}.json'
        if not path.exists():
            return None
        with open(path) as f:
            data = json.load(f)
        return Session.from_dict(data)

    def save(self, session: Session | None = None, tool_max_chars: int = 0,
             noise_tools: list[str] | None = None):
        s = session or self.current
        if s is None:
            return
        with open(self.sessions_dir / f'{s.name}.json', 'w') as f:
            json.dump(s.to_dict(tool_max_chars=tool_max_chars, noise_tools=noise_tools),
                      f, indent=2)

    def list(self) -> list[str]:
        return sorted(p.stem for p in self.sessions_dir.glob('*.json'))

    def delete(self, name: str) -> bool:
        path = self.sessions_dir / f'{name}.json'
        if path.exists():
            path.unlink()
            return True
        return False
