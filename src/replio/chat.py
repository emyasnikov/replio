import sys
import readline

from .config import Config
from .engine import Engine
from .ui import ReplUI
from . import get_version

HISTFILE = '.replio_history'


class ChatLoop(Engine):
    def __init__(self, config: Config):
        ui = ReplUI(self)
        super().__init__(config, ui=ui)
        self._load_history(config)
        self._setup_readline()

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
        readline.set_completer(self._completer)
        readline.parse_and_bind('tab: complete')

    def _completer(self, text: str, state: int) -> str | None:
        line = readline.get_line_buffer()
        for prefix in ('/session load ', '/session preview ', '/session delete '):
            if line.startswith(prefix):
                names = [n for n in self.sessions.list() if n.startswith(text)]
                if state < len(names):
                    return names[state] + ' '
                return None
        for prefix in ('/plugins enable ', '/plugins disable ',
                       '/plugins update ', '/plugins uninstall '):
            if line.startswith(prefix):
                pm = getattr(self, '_plugin_manager', None)
                names = [i.name for i in pm.status()] if pm else []
                options = sorted(n for n in names if n.startswith(text))
                if state < len(options):
                    return options[state] + ' '
                return None
        term = text[1:] if text.startswith('/') else text
        options = sorted(c for c in self.registry.commands if c.startswith(term))
        if state < len(options):
            name = options[state]
            return ('/' + name if text.startswith('/') else name) + ' '
        return None

    def run(self):
        system_prompt = self.config.get('system_prompt', '')
        if system_prompt:
            self.current_session.add_message('system', system_prompt)

        if self.config.get('clear_screen', True):
            sys.stdout.write('\033[3J\033[2J\033[H')
            sys.stdout.flush()

        model_str = self.config.get('model', '?')
        provider_str = self.config.get('provider', '?')
        if self.config.get('show_version', True):
            print(f'REPL.io v{get_version()} ({provider_str}: {model_str})  /help for commands')
        else:
            print(f'REPL.io ({provider_str}: {model_str})  /help for commands')

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

            try:
                if line.startswith('/'):
                    self.current_session.add_message('command', line)
                    self.registry.dispatch(line)
                    self.session_auto_save()
                else:
                    self.chat(line)
            except Exception as e:
                self.current_session.add_error(0, str(e))
                print(f'\001\033[91m\002[Error]\001\033[0m\002 {e}')

        self._save_history()
