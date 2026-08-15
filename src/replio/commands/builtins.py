import sys
import json

from .. import get_version

SUB_INDENT = 4


def _command_label(name, aliases):
    label = '/' + name
    if aliases:
        label += ', /' + ', /'.join(aliases)
    return label


def _render_commands(registry, names):
    metas = {n: registry.meta.get(n, {}) for n in names}
    labels = {n: _command_label(n, metas[n].get('aliases', [])) for n in names}
    max_label = max((len(l) for l in labels.values()), default=0)
    desc_col = 2 + max_label + 2
    for n in names:
        print(f'  {labels[n]:<{desc_col - 2}}{metas[n].get("description", "")}')
        for sub, sdesc in metas[n].get('subcommands', []):
            print(f'{" " * SUB_INDENT}{sub:<{desc_col - SUB_INDENT}}{sdesc}')


def _render_tools(chat):
    chat._init_tooling()
    if not chat._tool_registry or not chat._tool_policy:
        print('  (tool calling disabled)')
        return
    allowed = sorted(n for n in chat._tool_registry.names()
                     if chat._tool_policy.allowed(n))
    if not allowed:
        print('  (no tools allowed)')
        return
    rows = [(n, chat._tool_registry.info(n)) for n in allowed]
    name_w = max(len(n) for n, _ in rows)
    for n, info in rows:
        print(f'  {n:<{name_w + 2}}{info["short"]}')


def _render_tool_detail(chat, name):
    info = chat._tool_registry.info(name)
    if not info:
        print(f'No help available for "{name}"')
        return
    action = chat._tool_policy.action(name, info['permission'])
    print(name)
    print(f'  {info["description"]}')
    print(f'  category: {info["category"]}')
    print(f'  permission: {info["permission"]}: {action}')
    props = info['parameters'].get('properties', {})
    required = info['parameters'].get('required', [])
    if props:
        print('  params:')
        for p, spec in props.items():
            req = 'required' if p in required else 'optional'
            print(f'    {p} ({req}): {spec.get("description", "")}')


def register_builtins(registry):
    chat = registry.chat_loop

    @registry.register('help', aliases=['h'],
                       description='Show available commands and tools (use /help <cmd|tool> for details)')
    def help_cmd(arg=''):
        arg = arg.strip().lstrip('/')
        if arg:
            canonical = registry.canonical(arg)
            if canonical:
                _render_commands(registry, [canonical])
                return
            chat._init_tooling()
            if chat._tool_registry and chat._tool_registry.info(arg):
                _render_tool_detail(chat, arg)
                return
            print(f'No help available for "{arg}"')
            return
        print('Available commands:')
        _render_commands(registry, sorted(registry.meta))
        print()
        print('Available tools:')
        _render_tools(chat)

    @registry.register('exit', aliases=['quit', 'q'], description='Exit the REPL')
    def exit_cmd(_=None):
        chat.session_auto_save()
        sys.exit(0)

    @registry.register('version', aliases=['v'], description='Show the REPL.io version')
    def version_cmd(_=None):
        print(f'REPL.io {get_version()}')

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
        from ..providers import PROVIDERS, detect_provider
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

        chat.config.set('base_url', base_url)
        detected = detect_provider(base_url)
        if detected in PROVIDERS and detected != 'openai-compatible' and detected != provider:
            print(f'  Detected provider "{detected}" from base URL — switching')
            provider = detected
        chat.config.set('provider', provider)
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
        ('preview', 'Show a structural preview of a session'),
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
            chat.current_session = chat.sessions.create()
            print(f'New session: {chat.current_session.name}')
        elif action == 'list':
            sessions = chat.sessions.list()
            if sessions:
                current = chat.sessions.current.name if chat.sessions.current else ''
                for s in sessions:
                    marker = '  <-- current' if s == current else ''
                    print(f'  {s}{marker}')
            else:
                print('  No sessions found')
        elif action == 'preview':
            name = parts[1] if len(parts) > 1 else ''
            if not name:
                print('Usage: /session preview <name>')
                return
            s = chat.preview_session(name)
            if s is None:
                print(f'Session not found: {name}')
        elif action == 'load':
            name = parts[1] if len(parts) > 1 else ''
            if not name:
                print('Usage: /session load <name>')
                return
            s = chat.sessions.load(name)
            if s:
                chat.current_session = s
                n, chars = chat._context_size()
                print(f'Loaded session: {name} — {n} messages · '
                      f'{chat._human_chars(chars)} context')
                chat.preview_session(name, session=s)
                chat.current_session.add_message('command', f'/session load {name}')
                try:
                    answer = input(
                        '  Summarize & trim history before continuing? [y/N] '
                    ).strip().lower()
                except (EOFError, KeyboardInterrupt):
                    print()
                    return
                if answer in ('y', 'yes'):
                    chat.compact_session()
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

    @registry.register('compact', aliases=['c'],
                       description='Summarize the conversation and trim the context')
    def compact_cmd(_=None):
        chat.compact_session()

    @registry.register('tool', description='Run a tool directly (no args lists tools)')
    def tool_cmd(arg=''):
        chat._init_tooling()
        if not chat._tool_registry or not chat._tool_policy:
            print('Tool calling is disabled (tool_calling: false)')
            return
        parts = arg.strip().split(maxsplit=1)
        if not arg:
            allowed = sorted(n for n in chat._tool_registry.names()
                             if chat._tool_policy.allowed(n))
            if not allowed:
                print('No tools allowed')
                return
            print('Available tools:')
            for n in allowed:
                print(f'  {n}')
            print('Use /help <tool> for details')
            return
        name = parts[0]
        args_str = parts[1] if len(parts) > 1 else '{}'
        try:
            arguments = json.loads(args_str) if args_str else {}
        except json.JSONDecodeError:
            print('Usage: /tool <name> {"key": "value"}')
            return
        print(chat._run_tool(name, arguments))
