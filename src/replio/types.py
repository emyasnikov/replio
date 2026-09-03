import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from .config import Config


@dataclass
class AgentType:
    name: str
    system_prompt: str = ''
    model: str = ''
    skills: list = field(default_factory=list)
    tags: list = field(default_factory=list)
    tool_permission: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict) -> 'AgentType':
        return cls(
            name=d.get('name', ''),
            system_prompt=d.get('system_prompt', ''),
            model=d.get('model', ''),
            skills=list(d.get('skills') or []),
            tags=list(d.get('tags') or []),
            tool_permission=dict(d.get('tool_permission') or {}),
        )

    def to_body(self) -> dict:
        body = asdict(self)
        body.pop('name', None)
        return {k: v for k, v in body.items() if v not in ('', [], {})}


def _load_scope(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    try:
        with open(path) as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    out: dict[str, dict[str, Any]] = {}
    if isinstance(data, dict):
        for name, d in data.items():
            if isinstance(d, dict):
                entry = dict(d)
                entry.setdefault('name', str(name))
                out[str(name)] = entry
    elif isinstance(data, list):
        for d in data:
            if isinstance(d, dict) and d.get('name'):
                out[str(d['name'])] = dict(d)
    return out


class TypeRegistry:
    BUNDLED_FILENAME = 'bundled_types.json'

    def __init__(self, global_dir: Path | None = None,
                 local_path: Path | None = None,
                 bundled_path: Path | None = None):
        base = global_dir if global_dir is not None else (Config.GLOBAL_DIR or Path.home())
        self.global_path = base / '.config' / 'replio' / 'types.json'
        self.local_path = Path(local_path) if local_path is not None else (
            Path.cwd() / '.replio' / 'types.json')
        self.bundled_path = Path(bundled_path) if bundled_path is not None else (
            Path(__file__).with_name(self.BUNDLED_FILENAME))
        self._bundled: dict[str, dict[str, Any]] = {}
        self._global: dict[str, dict[str, Any]] = {}
        self._local: dict[str, dict[str, Any]] = {}
        self._plugins: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self):
        self._bundled = _load_scope(self.bundled_path)
        self._global = _load_scope(self.global_path)
        self._local = _load_scope(self.local_path)

    def add_plugin(self, entry: dict) -> None:
        if not isinstance(entry, dict) or not entry.get('name'):
            return
        self._plugins[str(entry['name'])] = dict(entry)

    def reload(self, plugin_manager=None) -> None:
        self._load()
        self._plugins = {}
        if plugin_manager is not None:
            register = getattr(plugin_manager, 'register_types', None)
            if register:
                register(self)

    def _save_scope(self, scope: str):
        path = self.global_path if scope == 'global' else self.local_path
        raw = self._global if scope == 'global' else self._local
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix('.json.tmp')
        tmp.write_text(json.dumps(raw, indent=2))
        os.replace(tmp, path)

    def _merged_entries(self) -> dict[str, dict[str, Any]]:
        names = (set(self._bundled) | set(self._plugins)
                 | set(self._global) | set(self._local))
        merged: dict[str, dict[str, Any]] = {}
        for name in names:
            entry: dict[str, Any] = {}
            entry.update(self._bundled.get(name, {}))
            entry.update(self._plugins.get(name, {}))
            entry.update(self._global.get(name, {}))
            entry.update(self._local.get(name, {}))
            entry['name'] = name
            merged[name] = entry
        return merged

    def all(self) -> list[AgentType]:
        return sorted(
            (AgentType.from_dict(e) for e in self._merged_entries().values()),
            key=lambda p: p.name)

    def names(self) -> list[str]:
        return sorted(self._merged_entries())

    def find(self, name: str) -> AgentType | None:
        entry = self._merged_entries().get(name)
        return AgentType.from_dict(entry) if entry is not None else None

    def origin(self, name: str) -> str:
        has_local = name in self._local
        has_global = name in self._global
        has_bundled = name in self._bundled
        has_plugin = name in self._plugins
        if not any((has_local, has_global, has_bundled, has_plugin)):
            return ''
        layers = sum((has_local, has_global, has_bundled, has_plugin))
        if layers == 1:
            if has_local:
                return 'local'
            if has_global:
                return 'global'
            if has_plugin:
                return 'plugin'
            return 'bundled'
        return 'merged'

    def is_bundled(self, name: str) -> bool:
        return name in self._bundled

    def put(self, agent_type: AgentType, scope: str = 'local') -> AgentType:
        raw = self._local if scope == 'local' else self._global
        raw[agent_type.name] = agent_type.to_body()
        self._save_scope(scope)
        return agent_type

    def remove(self, name: str, scope: str = 'local') -> bool:
        raw = self._local if scope == 'local' else self._global
        if name in raw:
            del raw[name]
            self._save_scope(scope)
            return True
        return False