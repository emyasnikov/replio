import sys
import readline
import os
from datetime import datetime, timezone

from .config import Config
from .providers.ollama import OllamaProvider
from .sessions.manager import SessionManager
from .commands.registry import CommandRegistry
from .commands.builtins import register_builtins

HISTFILE = '.replai_history'


class ChatLoop:
    def __init__(self, config: Config):
        self.config = config
        self.provider = None
        self._reinit_provider()

        sessions_dir = config.local_path.parent / 'sessions'
        self.sessions = SessionManager(sessions_dir)
        self.current_session = self.sessions.create()
        self._load_history(config)
        self.registry = CommandRegistry(self)
        register_builtins(self.registry)
        self._setup_readline()

    def _reinit_provider(self):
        provider_name = self.config.get('provider', 'ollama')
        if provider_name == 'ollama':
            self.provider = OllamaProvider(
                base_url=self.config.get('base_url'),
                api_key=self.config.get('api_key'),
                model=self.config.get('model'),
                temperature=self.config.get('temperature'),
                max_tokens=self.config.get('max_tokens'),
            )
        else:
            print(f'Unknown provider "{provider_name}", falling back to ollama')
            self.config.set('provider', 'ollama')
            self._reinit_provider()

    def _load_history(self, config):
        hist = config.local_path.parent / HISTFILE
        if hist.exists():
            try:
                readline.read_history_file(str(hist))
            except OSError:
                pass
        readline.set_history_length(1000)

    def _save_history(self):
        hist = self.config.local_path.parent / HISTFILE
        try:
            hist.parent.mkdir(parents=True, exist_ok=True)
            readline.write_history_file(str(hist))
        except OSError:
            pass

    def _setup_readline(self):
        commands = sorted(set(self.registry.commands.keys()))

        def completer(text, state):
            if text.startswith('/'):
                options = [c for c in commands if c.startswith(text)]
                if state < len(options):
                    return options[state] + ' '
            return None

        readline.set_completer(completer)
        readline.parse_and_bind('tab: complete')

    def session_auto_save(self):
        if self.current_session and self.current_session.messages:
            self.sessions.save(self.current_session)

    def run(self):
        system_prompt = self.config.get('system_prompt', '')
        if system_prompt:
            self.current_session.add_message('system', system_prompt)

        model_str = self.config.get('model', '?')
        print(f'REPL.ai  |  model: {model_str}  |  /help for commands')

        while True:
            try:
                line = input('\001\033[36m\002>>>\001\033[0m\002 ').strip()
            except (EOFError, KeyboardInterrupt):
                print()
                self.session_auto_save()
                self._save_history()
                break

            if not line:
                continue

            if line.startswith('/'):
                self.current_session.add_message('command', line)
                self.registry.dispatch(line)
                self.session_auto_save()
            else:
                self._handle_message(line)

        self._save_history()

    def _handle_message(self, content):
        now = datetime.now(timezone.utc)
        self.current_session.add_message(
            'user', content, timestamp=now.isoformat(timespec='seconds')
        )
        self.session_auto_save()

        print('\001\033[90m\002\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\001\033[0m\002')
        messages = self.current_session.messages
        full_response = ''
        start = datetime.now(timezone.utc)

        for event in self.provider.chat(messages):
            t = event.get('type', '')
            if t == 'token':
                token = event['content']
                sys.stdout.write(token)
                sys.stdout.flush()
                full_response += token
            elif t == 'error':
                code = event.get('code', '')
                msg = event.get('message', 'Unknown error')
                print(f'\001\033[91m\002[Error {code}]\001\033[0m\002 {msg}')
                break
            elif t == 'done':
                elapsed = (datetime.now(timezone.utc) - start).total_seconds()
                print()
                print(f'\001\033[90m\002({elapsed:.1f}s)\001\033[0m\002')
                break

        if full_response:
            end = datetime.now(timezone.utc)
            duration = (end - start).total_seconds()
            self.current_session.add_message(
                'assistant', full_response,
                timestamp=end.isoformat(timespec='seconds'),
                duration=round(duration, 1),
                model=self.config.get('model'),
                provider=self.config.get('provider'),
            )
            self.session_auto_save()
