import copy
import json
from pathlib import Path


DEFAULT_CONFIG = {
    'provider': 'ollama',
    'model': 'llama3.2',
    'base_url': 'https://api.ollama.com',
    'api_key': '',
    'temperature': 0.7,
    'max_tokens': 8192,
    'system_prompt': '',
    'mode': 'build',
    'modes': {
        'build': {'system_prompt': '', 'tool_permission': {}},
        'plan': {
            'system_prompt': (
                'You are in plan mode (read-only). Investigate, cite sources, and '
                'propose a plan; do not modify files or run commands. Write and '
                'exec tools are disabled.'
            ),
            'tool_permission': {'edit': 'deny', 'bash': 'deny'},
        },
    },
    'tool_calling': True,
    'tool_status_visible': True,
    'glyph_lines': True,
    'glyph_params': True,
    'show_errors': True,
    'tool_analysis': False,
    'session_tool_max_chars': 0,
    'tool_max_result_chars': 0,
    'connect_check': True,
    'stream_retries': 2,
    'stream_retry_delay': 0.5,
    'query_refine': False,
    'query_refine_min_words': 3,
    'query_refine_context': 4,
    'show_thinking': False,
    'reasoning': 'auto',
    'markdown_streaming': False,
    'word_streaming': True,
    'show_context_size': True,
    'clear_screen': True,
    'show_version': True,
    'compact_keep': 4,
    'noise_tools': ['fetch_page'],
    'web_search': False,
    'search_results': 5,
    'tools.allow': [],
    'tools.deny': [],
    'tool_permission': {
        'bash': 'ask',
        'edit': 'allow',
        'list': 'allow',
        'mcp': 'ask',
        'read': 'allow',
        'web': 'allow',
    },
    'mcp.servers': [],
    'mcp_server.allow_ask': True,
    'plugins': ['replio-core-websearch', 'replio-core-fs', 'replio-core-exec', 'replio-core-mcp'],
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
        self._migrate()

    def _migrate(self):
        if 'plugins.enabled' in self.data or 'plugins.deny' in self.data:
            plugins = list(self.data.get('plugins') or DEFAULT_CONFIG['plugins'])
            enabled = self.data.pop('plugins.enabled', None)
            denied = self.data.pop('plugins.deny', None)
            if enabled is not None:
                plugins = [str(n) for n in enabled] if enabled else []
            if denied:
                blocked = set(str(n) for n in denied)
                plugins = [n for n in plugins if n not in blocked]
            self.data['plugins'] = plugins

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
