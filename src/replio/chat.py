import sys
import readline
from pathlib import Path

from .config import Config
from .engine import Engine
from .ui import ReplUI
from . import get_version

HISTFILE = '.replio_history'

MAIN_PROMPT = '\001\033[36m\002>>>\001\033[0m\002 '
CONT_PROMPT = '\001\033[36m\002...\001\033[0m\002 '


def _open_delim(text: str) -> str | None:
    if _overlap_count(text, '"""') % 2 == 1:
        return '"""'
    if _overlap_count(text, "'''") % 2 == 1:
        return "'''"
    return None


def _overlap_count(text: str, delim: str) -> int:
    n = 0
    i = text.find(delim)
    while i != -1:
        n += 1
        i = text.find(delim, i + 1)
    return n


def _strip_framing(text: str, delim: str) -> str:
    first = text.find(delim)
    last = text.rfind(delim)
    if first == -1 or last <= first:
        return text
    return (text[:first] + text[first + len(delim):last]
            + text[last + len(delim):]).strip('\n')


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
        readline.set_completer_delims(' \t\n')
        if 'libedit' in (readline.__doc__ or ''):
            readline.parse_and_bind('bind ^I rl_complete')
        else:
            readline.parse_and_bind('tab: complete')

    def _completer(self, text: str, state: int) -> str | None:
        line = readline.get_line_buffer()
        head = line[: len(line) - len(text)]
        for prefix in ('/session load ', '/session preview ', '/session delete ', '/session export '):
            if head.endswith(prefix):
                names = [n for n in self.sessions.list() if n.startswith(text)]
                if state < len(names):
                    return names[state] + ' '
                return None
        for prefix in ('/plugins enable ', '/plugins disable ',
                       '/plugins update ', '/plugins uninstall '):
            if head.endswith(prefix):
                pm = getattr(self, '_plugin_manager', None)
                names = [i.name for i in pm.status()] if pm else []
                options = sorted(n for n in names if n.startswith(text))
                if state < len(options):
                    return options[state] + ' '
                return None
        if head.endswith('/tool '):
            options = sorted(n for n in self._tool_names() if n.startswith(text))
            if state < len(options):
                return options[state] + ' '
            return None
        if head.endswith('/mode '):
            from .modes import mode_list
            options = sorted(m.name for m in mode_list(self.config)
                             if m.name.startswith(text))
            if state < len(options):
                return options[state] + ' '
            return None
        if head.lstrip().startswith('/'):
            cmd = head.lstrip()[1:].strip().split(maxsplit=1)[0]
            meta = self.registry.meta.get(cmd)
            if meta and meta.get('subcommands'):
                options = sorted(n for n, _ in meta['subcommands']
                                 if n.startswith(text))
                if state < len(options):
                    return options[state] + ' '
                return None
            return self._path_complete(text, state)
        if text.startswith('/'):
            term = text[1:]
            options = sorted(c for c in self.registry.commands if c.startswith(term))
            if state < len(options):
                return '/' + options[state] + ' '
            return None
        return None

    def _tool_names(self):
        if not getattr(self, '_tool_registry', None):
            return []
        policy = getattr(self, '_tool_policy', None)
        names = self._tool_registry.names()
        if policy is None:
            return names
        return [n for n in names
                if policy.allowed(n, self._tool_registry.permission_for(n))]

    def _path_complete(self, text: str, state: int) -> str | None:
        path = Path(text) if text else Path('.')
        name = path.name
        parent = path.parent if str(path.parent) else Path('.')
        try:
            options = sorted(p for p in parent.glob(name + '*'))
        except OSError:
            options = []
        if state < len(options):
            cand = options[state]
            return str(cand) + ('/' if cand.is_dir() else ' ')
        return None

    def _read_line(self) -> str | None:
        try:
            line = input(MAIN_PROMPT).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return None
        delim = _open_delim(line)
        if delim is None:
            return line
        parts = [line]
        while True:
            try:
                parts.append(input(CONT_PROMPT).rstrip())
            except (EOFError, KeyboardInterrupt):
                print()
                return None
            buffer = '\n'.join(parts)
            if _overlap_count(buffer, delim) % 2 == 0:
                composed = _strip_framing(buffer, delim)
                try:
                    readline.add_history(composed)
                except Exception:
                    pass
                return composed

    def run(self):
        if self.config.get('clear_screen', True):
            sys.stdout.write('\033[3J\033[2J\033[H')
            sys.stdout.flush()

        model_str = self.config.get('model', '?')
        provider_str = self.config.get('provider', '?')
        mode_str = self.config.get('mode', 'build')
        suffix = f'  [{mode_str} mode]' if mode_str != 'build' else ''
        if self.config.get('show_version', True):
            print(f'Replio v{get_version()} ({provider_str}: {model_str}){suffix}  /help for commands')
        else:
            print(f'Replio ({provider_str}: {model_str}){suffix}  /help for commands')

        while True:
            line = self._read_line()
            if line is None:
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
