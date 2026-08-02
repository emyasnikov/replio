import tempfile
import json
from pathlib import Path
from unittest.mock import MagicMock

from replio.config import Config
from replio.chat import ChatLoop
from replio.sessions.manager import SessionManager
from replio.commands.registry import CommandRegistry
from replio.commands.builtins import register_builtins


def make_chat(config_data: dict | None = None) -> ChatLoop:
    temp_dir = tempfile.TemporaryDirectory()
    data = {
        'tool_calling': True,
        'provider': 'ollama',
        'model': 'test-model',
        'base_url': 'https://test.api.com',
        'api_key': '',
        'temperature': 0.7,
        'max_tokens': 2048,
    }
    if config_data:
        data.update(config_data)

    config_dir = Path(temp_dir.name) / '.replio'
    config_dir.mkdir(parents=True, exist_ok=True)
    with open(config_dir / 'config.json', 'w') as f:
        json.dump(data, f)

    config = Config(path=temp_dir.name)

    chat = ChatLoop.__new__(ChatLoop)
    chat.config = config
    chat.provider = MagicMock()
    sessions_dir = config.local_path.parent / 'sessions'
    chat.sessions = SessionManager(sessions_dir)
    chat.current_session = chat.sessions.create()
    chat._tool_registry = None

    chat._perform_search = MagicMock(return_value='Mocked search context.')
    chat._show_tool_status = MagicMock()
    chat.session_auto_save = MagicMock()
    chat._tmp = temp_dir

    chat.registry = CommandRegistry(chat)
    register_builtins(chat.registry)
    return chat
