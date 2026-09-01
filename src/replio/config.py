import copy
import json
from pathlib import Path


DEFAULT_CONFIG = {
    'provider': 'ollama',
    'model': 'llama3.2',
    'base_url': 'https://api.ollama.com',
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
    'delegate_echo': True,
    'glyph_lines': True,
    'glyph_params': True,
    'show_errors': True,
    'show_notes': True,
    'tool_analysis': False,
    'session_tool_max_chars': 0,
    'tool_max_result_chars': 100000,
    'list_dir_max_entries': 200,
    'connect_check': True,
    'stream_retries': 2,
    'stream_retry_delay': 0.5,
    'auto_continue': True,
    'auto_continue_max': 2,
    'query_refine': False,
    'query_refine_min_words': 3,
    'query_refine_context': 4,
    'show_thinking': False,
    'show_thought_duration': True,
    'reasoning': 'auto',
    'markdown_streaming': False,
    'word_streaming': True,
    'show_context_size': True,
    'footer_tokens': ['context'],
    'clear_screen': True,
    'show_version': True,
    'compact_keep': 4,
    'noise_tools': ['web_fetch', 'open', 'fetch_page'],
    'web_search': False,
    'search_results': 5,
    'tools.allow': [],
    'tools.deny': [],
    'tool_permission': {
        'bash': 'ask',
        'delegate': 'allow',
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

_MISSING = object()


class Config:
    GLOBAL_DIR: Path | None = None

    def __init__(self, path: str | None = None):
        global_home = self.GLOBAL_DIR if self.GLOBAL_DIR is not None else Path.home()
        self.global_path = global_home / '.config' / 'replio' / 'config.json'
        if path:
            self.local_path = Path(path).resolve() / '.replio' / 'config.json'
        else:
            self.local_path = Path.cwd() / '.replio' / 'config.json'
        self.data = copy.deepcopy(DEFAULT_CONFIG)
        self._global_raw: dict = {}
        self._local_raw: dict = {}
        self._load()

    def _load(self):
        if self.global_path.exists():
            with open(self.global_path) as f:
                self._global_raw = json.load(f)
            self.data.update(self._global_raw)
        if self.local_path.exists():
            with open(self.local_path) as f:
                self._local_raw = json.load(f)
            self.data.update(self._local_raw)

    def reload(self):
        self.data = copy.deepcopy(DEFAULT_CONFIG)
        self._global_raw = {}
        self._local_raw = {}
        self._load()

    def get(self, key, default=None):
        return self.data.get(key, default)

    def apply(self, key, value):
        self.data[key] = value

    def set(self, key, value, scope: str = 'local'):
        raw = self._global_raw if scope == 'global' else self._local_raw
        raw[key] = value
        if scope == 'global':
            local_value = self._local_raw.get(key)
            if local_value == '':
                local_value = None
            if key not in self._local_raw or local_value is None:
                self.data[key] = value
            self._write_global({})
        else:
            self.data[key] = value
            self._save_local()

    def unset(self, key, scope: str = 'local'):
        raw = self._global_raw if scope == 'global' else self._local_raw
        raw.pop(key, None)
        other_raw = self._local_raw if scope == 'global' else self._global_raw
        fallback = other_raw.get(key, _MISSING)
        if fallback is not _MISSING:
            self.data[key] = fallback
        elif key in DEFAULT_CONFIG:
            self.data[key] = copy.deepcopy(DEFAULT_CONFIG[key])
        else:
            self.data.pop(key, None)
        if scope == 'global':
            self._write_global({})
        else:
            self._save_local()

    def origin(self, key: str) -> str:
        if key in self._local_raw:
            return 'local'
        if key in self._global_raw:
            return 'global'
        return 'default'

    def save(self):
        self._save_local()

    def _save_local(self):
        self.local_path.parent.mkdir(parents=True, exist_ok=True)
        self.local_path.write_text(json.dumps(self._local_raw, indent=2))

    def _write_global(self, patch: dict):
        self._global_raw.update(patch)
        self.global_path.parent.mkdir(parents=True, exist_ok=True)
        self.global_path.write_text(json.dumps(self._global_raw, indent=2))