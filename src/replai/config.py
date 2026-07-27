import json
from pathlib import Path


DEFAULT_CONFIG = {
    'provider': 'ollama',
    'model': 'llama3.2',
    'base_url': 'https://api.ollama.com',
    'api_key': '',
    'temperature': 0.7,
    'max_tokens': 2048,
    'system_prompt': '',
}


class Config:
    def __init__(self, path: str | None = None):
        self.global_path = Path.home() / '.config' / 'replai' / 'config.json'
        if path:
            self.local_path = Path(path).resolve() / '.replai' / 'config.json'
        else:
            self.local_path = Path.cwd() / '.replai' / 'config.json'
        self.data = dict(DEFAULT_CONFIG)
        self._load()

    def _load(self):
        for p in [self.global_path, self.local_path]:
            if p.exists():
                with open(p) as f:
                    self.data.update(json.load(f))

    def save(self):
        self.local_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.local_path, 'w') as f:
            json.dump(self.data, f, indent=2)

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()
