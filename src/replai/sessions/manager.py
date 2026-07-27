import json
from datetime import datetime
from pathlib import Path


class Session:
    def __init__(self, name: str, messages: list | None = None):
        self.name = name
        self.messages = messages or []

    def add_message(self, role: str, content: str):
        self.messages.append({'role': role, 'content': content})

    def to_dict(self):
        return {'name': self.name, 'messages': self.messages}

    @classmethod
    def from_dict(cls, data):
        return cls(data['name'], data.get('messages', []))


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
