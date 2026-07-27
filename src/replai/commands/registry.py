from typing import Callable


class CommandRegistry:
    def __init__(self, chat_loop):
        self.chat_loop = chat_loop
        self.commands: dict[str, Callable] = {}

    def register(self, name: str, aliases: list[str] | None = None,
                 handler: Callable | None = None):
        if handler is None:
            def wrapper(fn):
                self.commands[name] = fn
                for alias in (aliases or []):
                    self.commands[alias] = fn
                return fn
            return wrapper
        self.commands[name] = handler
        for alias in (aliases or []):
            self.commands[alias] = handler

    def dispatch(self, line: str):
        parts = line.strip().split(maxsplit=1)
        cmd = parts[0].lstrip('/')
        arg = parts[1] if len(parts) > 1 else ''
        handler = self.commands.get(cmd)
        if handler:
            try:
                handler(arg)
            except TypeError:
                handler()
        else:
            print(f'Unknown command: /{cmd}. Type /help for available commands.')
