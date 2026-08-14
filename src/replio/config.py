import copy
import json
from pathlib import Path


DEFAULT_CONFIG = {
    'provider': 'ollama',
    'model': 'llama3.2',
    'base_url': 'https://api.ollama.com',
    'api_key': '',
    'temperature': 0.7,
    'max_tokens': 0,
    'system_prompt': '',
    'tool_calling': True,
    'tool_status_visible': True,
    'tool_analysis': False,
    'session_tool_max_chars': 0,
    'query_refine': False,
    'query_refine_min_words': 3,
    'query_refine_context': 4,
    'show_thinking': True,
    'markdown_streaming': False,
    'show_context_size': True,
    'clear_screen': True,
    'compact_keep': 4,
    'noise_tools': ['fetch_page'],
    'web_search': False,
    'search_results': 5,
    'tools.allow': [],
    'tools.deny': [],
    'tool_permission': {
        'read': 'allow',
        'list': 'allow',
        'edit': 'allow',
        'bash': 'ask',
        'web': 'allow',
    },
}


class Config:
    def __init__(self, path: str | None = None):
        self.global_path = Path.home() / '.config' / 'replio' / 'config.json'
        if path:
            self.local_path = Path(path).resolve() / '.replio' / 'config.json'
        else:
            self.local_path = Path.cwd() / '.replio' / 'config.json'
        self.data = copy.deepcopy(DEFAULT_CONFIG)
        self._load()

    def _load(self):
        for p in [self.global_path, self.local_path]:
            if p.exists():
                with open(p) as f:
                    self.data.update(json.load(f))

    def reload(self):
        self.data = copy.deepcopy(DEFAULT_CONFIG)
        self._load()

    def save(self):
        self.local_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.local_path, 'w') as f:
            json.dump(self.data, f, indent=2)

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()
