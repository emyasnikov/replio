import sys
import json


def _command_label(name, aliases):
    label = '/' + name
    if aliases:
        label += ', /' + ', /'.join(aliases)
    return label


def _render_commands(registry, names):
    metas = {n: registry.meta.get(n, {}) for n in names}
    labels = {n: _command_label(n, metas[n].get('aliases', [])) for n in names}
    max_label = max((len(l) for l in labels.values()), default=0)
    sub_col = 2 + max((len(n) for n in names), default=0) + 1
    sub_len = max(
        (len(s) for m in metas.values() for s, _ in m.get('subcommands', [])),
        default=0,
    )
    desc_col = max(2 + max_label + 2, sub_col + sub_len + 2)
    for n in names:
        print(f'  {labels[n]:<{desc_col - 2}}{metas[n].get("description", "")}')
        for sub, sdesc in metas[n].get('subcommands', []):
            print(f'{" " * sub_col}{sub:<{desc_col - sub_col}}{sdesc}')


def register_builtins(registry):
    chat = registry.chat_loop

    @registry.register('help', aliases=['h'], description='Show available commands')
    def help_cmd(_=None):
        print('Available commands:')
        _render_commands(registry, sorted(registry.meta))

    @registry.register('exit', aliases=['quit', 'q'], description='Exit the REPL')
    def exit_cmd(_=None):
        chat.session_auto_save()
        sys.exit(0)

    @registry.register('model', description='Show or switch the active model')
    def model_cmd(arg=''):
        if arg:
            chat.config.set('model', arg.strip())
            chat.provider.model = chat.config.get('model')
            print(f'Model set to: {chat.config.get("model")}')
        else:
            print(f'Current model: {chat.config.get("model")}')

    @registry.register('provider', description='Show or switch the active provider')
    def provider_cmd(arg=''):
        if arg:
            chat.config.set('provider', arg.strip())
            chat._reinit_provider()
            print(f'Provider set to: {chat.config.get("provider")}')
        else:
            print(f'Current provider: {chat.config.get("provider")}')

    @registry.register('connect', description='Set up provider connection interactively')
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

    @registry.register('config', description='Show, get, or set config values')
    def config_cmd(arg=''):
        parts = arg.strip().split(maxsplit=1)
        if not arg:
            for k, v in chat.config.data.items():
                val = '***' if k == 'api_key' and v else v
                print(f'  {k}: {val}')
            return
        key = parts[0]
        rest = parts[1].strip() if len(parts) > 1 else ''

        if key == 'reload' and not rest:
            old = {k: chat.config.get(k) for k in ('provider', 'base_url', 'model')}
            chat.config.reload()
            print('Config reloaded from disk')
            for k in ('provider', 'base_url', 'model'):
                if chat.config.get(k) != old[k]:
                    print(f'  {k}: {old[k]} → {chat.config.get(k)} — run /provider or /connect to apply')
            return

        if not rest:
            val = chat.config.get(key)
            if key == 'api_key':
                val = '***' if val else val
            print(f'  {key}: {val}')
            return

        if rest in ('-a', '-r') or rest.startswith('-a ') or rest.startswith('-r '):
            op = rest[:2]
            items = rest[2:].strip().split()
            current = chat.config.get(key)
            if not isinstance(current, list):
                print(f'Config {key} is not a list — cannot add/remove items')
                return
            changed = False
            for it in items:
                if op == '-a' and it not in current:
                    current.append(it)
                    changed = True
                elif op == '-r' and it in current:
                    current.remove(it)
                    changed = True
            if changed:
                chat.config.set(key, current)
                print(f'Config {key} = {current}')
            else:
                print(f'Config {key} unchanged ({current})')
            return

        if key not in chat.config.data:
            try:
                answer = input(
                    f'Unknown config key "{key}". Store anyway? [y/N] '
                ).strip().lower()
            except (EOFError, KeyboardInterrupt):
                print()
                return
            if answer not in ('y', 'yes'):
                print('Skipped')
                return

        try:
            value = json.loads(rest)
        except json.JSONDecodeError:
            value = rest
        chat.config.set(key, value)
        print(f'Config {key} = {value}')

    @registry.register('session', description='Manage saved sessions', subcommands=[
        ('new', 'Start a new session'),
        ('list', 'List saved sessions'),
        ('load', 'Load a session'),
        ('delete', 'Delete a session'),
        ('save', 'Save the current session'),
    ])
    def session_cmd(arg=''):
        parts = arg.strip().split(maxsplit=1)
        action = parts[0] if parts else ''

        if not action:
            _render_commands(registry, ['session'])
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

    @registry.register('tool', description='Run a tool directly (no args lists tools)')
    def tool_cmd(arg=''):
        chat._init_tooling()
        if not chat._tool_registry or not chat._tool_policy:
            print('Tool calling is disabled (tool_calling: false)')
            return
        parts = arg.strip().split(maxsplit=1)
        if not arg:
            allowed = [n for n in chat._tool_registry.names()
                       if chat._tool_policy.allowed(n)]
            print('Available tools: ' + ', '.join(allowed))
            return
        name = parts[0]
        args_str = parts[1] if len(parts) > 1 else '{}'
        try:
            arguments = json.loads(args_str) if args_str else {}
        except json.JSONDecodeError:
            print('Usage: /tool <name> {"key": "value"}')
            return
        print(chat._run_tool(name, arguments))
