import json
from datetime import datetime, timezone
from pathlib import Path


class Session:
    def __init__(self, name: str, messages: list | None = None, model: str = ''):
        self.name = name
        self.messages = messages or []
        self.model = model

    def add_message(self, role: str, content: str, **kwargs):
        msg = {'role': role, 'content': content}
        msg['timestamp'] = kwargs.pop(
            'timestamp', datetime.now(timezone.utc).isoformat(timespec='seconds')
        )
        msg.update(kwargs)
        self.messages.append(msg)

    def to_dict(self):
        result = {'name': self.name, 'messages': self.messages}
        if self.model:
            result['model'] = self.model
        return result

    @classmethod
    def from_dict(cls, data):
        return cls(
            data['name'], data.get('messages', []), data.get('model', '')
        )


class SessionManager:
    def __init__(self, sessions_dir: Path):
        self.sessions_dir = sessions_dir
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.current: Session | None = None

    def create(self, name: str | None = None, model: str = '') -> Session:
        if not name:
            name = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.current = Session(name, model=model)
        return self.current

    def load(self, name: str) -> Session | None:
        path = self.sessions_dir / f'{name}.json'
        if not path.exists():
            return None
        with open(path) as f:
            data = json.load(f)
        self.current = Session.from_dict(data)
        return self.current

    def save(self, session: Session | None = None):
        s = session or self.current
        if s is None:
            return
        with open(self.sessions_dir / f'{s.name}.json', 'w') as f:
            json.dump(s.to_dict(), f, indent=2)

    def list(self) -> list[str]:
        return sorted(p.stem for p in self.sessions_dir.glob('*.json'))

    def delete(self, name: str) -> bool:
        path = self.sessions_dir / f'{name}.json'
        if path.exists():
            path.unlink()
            return True
        return False
