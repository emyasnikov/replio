import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path

from .config import Config


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


@dataclass
class ModelEntry:
    provider: str = 'ollama'
    base_url: str = ''
    model: str = ''
    api_key: str = ''
    added_at: str = ''
    last_used: str = ''

    @classmethod
    def from_dict(cls, d: dict) -> 'ModelEntry':
        return cls(
            provider=d.get('provider', 'ollama'),
            base_url=d.get('base_url', ''),
            model=d.get('model', ''),
            api_key=d.get('api_key', ''),
            added_at=d.get('added_at', ''),
            last_used=d.get('last_used', ''),
        )


class ModelRegistry:
    def __init__(self, global_dir: Path | None = None):
        base = global_dir if global_dir is not None else (Config.GLOBAL_DIR or Path.home())
        self.path = base / '.config' / 'replio' / 'models.json'
        self._entries: list[ModelEntry] = []
        self._load()

    def _load(self):
        if not self.path.exists():
            self._entries = []
            return
        try:
            with open(self.path) as f:
                data = json.load(f)
            self._entries = [ModelEntry.from_dict(d) for d in data if isinstance(d, dict)]
        except (OSError, ValueError):
            self._entries = []

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix('.json.tmp')
        tmp.write_text(json.dumps([asdict(e) for e in self._entries], indent=2))
        os.replace(tmp, self.path)
        if any(e.api_key for e in self._entries):
            try:
                os.chmod(self.path, 0o600)
            except OSError:
                pass

    def all(self) -> list[ModelEntry]:
        return list(self._entries)

    def find(self, provider: str, base_url: str, model: str) -> ModelEntry | None:
        for e in self._entries:
            if e.provider == provider and e.base_url == base_url and e.model == model:
                return e
        return None

    def api_key_for(self, provider: str, base_url: str, model: str) -> str:
        entry = self.find(provider, base_url, model)
        return entry.api_key if entry is not None else ''

    def put(self, provider: str, base_url: str, model: str, api_key: str = '') -> ModelEntry:
        now = _now()
        entry = self.find(provider, base_url, model)
        if entry is None:
            entry = ModelEntry(provider=provider, base_url=base_url, model=model,
                               added_at=now, last_used=now, api_key=api_key)
            self._entries.append(entry)
        else:
            entry.last_used = now
            if api_key:
                entry.api_key = api_key
        self._sink()
        return entry

    def touch(self, provider: str, base_url: str, model: str) -> ModelEntry | None:
        entry = self.find(provider, base_url, model)
        if entry is None:
            return None
        entry.last_used = _now()
        self._sink()
        return entry

    def remove(self, provider: str, base_url: str, model: str) -> bool:
        entry = self.find(provider, base_url, model)
        if entry is None:
            return False
        self._entries.remove(entry)
        self._save()
        return True

    def grouped(self) -> list[tuple[str, list[ModelEntry]]]:
        groups: dict[str, list[ModelEntry]] = {}
        for e in self.all():
            key = e.provider if not e.base_url else f'{e.provider} ({e.base_url})'
            groups.setdefault(key, []).append(e)
        return list(groups.items())

    def _sink(self):
        self._entries.sort(key=lambda e: e.last_used, reverse=True)
        self._save()