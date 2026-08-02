import sys


def register_builtins(registry):
    chat = registry.chat_loop

    @registry.register('help', aliases=['h'])
    def help_cmd(_=None):
        print('Available commands:')
        seen = set()
        for name, fn in sorted(registry.commands.items()):
            if id(fn) not in seen:
                seen.add(id(fn))
                print(f'  /{name}')
                aliases = [k for k, v in registry.commands.items()
                           if v is fn and k != name]
                if aliases:
                    print(f'      aliases: {", ".join(aliases)}')

    @registry.register('exit', aliases=['quit', 'q'])
    def exit_cmd(_=None):
        chat.session_auto_save()
        sys.exit(0)

    @registry.register('model')
    def model_cmd(arg=''):
        if arg:
            chat.config.set('model', arg.strip())
            chat.provider.model = chat.config.get('model')
            print(f'Model set to: {chat.config.get("model")}')
        else:
            print(f'Current model: {chat.config.get("model")}')

    @registry.register('provider')
    def provider_cmd(arg=''):
        if arg:
            chat.config.set('provider', arg.strip())
            chat._reinit_provider()
            print(f'Provider set to: {chat.config.get("provider")}')
        else:
            print(f'Current provider: {chat.config.get("provider")}')

    @registry.register('connect')
    def connect_cmd(_=None):
        print('Setting up provider connection:')
        provider = input(
            f'  Provider [{chat.config.get("provider")}]: '
        ).strip() or chat.config.get('provider')
        base_url = input(
            f'  Base URL [{chat.config.get("base_url")}]: '
        ).strip() or chat.config.get('base_url')
        api_key = input('  API key (leave empty to skip): ').strip()
        model = input(
            f'  Model [{chat.config.get("model")}]: '
        ).strip() or chat.config.get('model')

        chat.config.set('provider', provider)
        chat.config.set('base_url', base_url)
        chat.config.set('model', model)
        if api_key:
            chat.config.set('api_key', api_key)

        chat._reinit_provider()
        print(f'Connected to {provider} ({base_url})')

    @registry.register('config')
    def config_cmd(arg=''):
        parts = arg.strip().split(maxsplit=1)
        if not arg:
            for k, v in chat.config.data.items():
                val = '***' if k == 'api_key' and v else v
                print(f'  {k}: {val}')
        elif len(parts) == 1:
            key = parts[0]
            val = chat.config.get(key)
            if key == 'api_key':
                val = '***' if val else val
            print(f'  {key}: {val}')
        else:
            key, value = parts
            chat.config.set(key, value)
            print(f'Config {key} = {value}')

    @registry.register('session')
    def session_cmd(arg=''):
        parts = arg.strip().split(maxsplit=1)
        action = parts[0] if parts else ''

        if not action:
            print('Session commands:')
            print('  /session new            start a new session')
            print('  /session list           list saved sessions')
            print('  /session load <name>    load a session')
            print('  /session delete <name>  delete a session')
            print('  /session save           save current session')
            return

        if action == 'new':
            s = chat.sessions.create()
            print(f'New session: {s.name}')
        elif action == 'list':
            sessions = chat.sessions.list()
            if sessions:
                current = chat.sessions.current.name if chat.sessions.current else ''
                for s in sessions:
                    marker = '  <-- current' if s == current else ''
                    print(f'  {s}{marker}')
            else:
                print('  No sessions found')
        elif action == 'load':
            name = parts[1] if len(parts) > 1 else ''
            if not name:
                print('Usage: /session load <name>')
                return
            s = chat.sessions.load(name)
            if s:
                print(f'Loaded session: {name} ({len(s.messages)} messages)')
            else:
                print(f'Session not found: {name}')
        elif action == 'delete':
            name = parts[1] if len(parts) > 1 else ''
            if not name:
                print('Usage: /session delete <name>')
                return
            if chat.sessions.delete(name):
                print(f'Deleted session: {name}')
            else:
                print(f'Session not found: {name}')
        elif action == 'save':
            chat.session_auto_save()
            print('Session saved')
