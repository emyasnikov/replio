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
        providers = dict(PROVIDERS)
        pm = getattr(chat, '_plugin_manager', None)
        if pm is not None:
            providers.update(pm.provider_classes())
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
        if detected in providers and detected != 'openai-compatible' and detected != provider:
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

    @registry.register('plugins', aliases=['plugin'],
                       description='Manage plugins', subcommands=[
        ('list', 'List installed plugins'),
        ('enable', 'Enable a plugin'),
        ('disable', 'Disable a plugin'),
        ('install', 'Install a plugin from a git URL or local path'),
        ('update', 'Update an installed plugin'),
        ('uninstall', 'Remove an installed plugin'),
    ])
    def plugins_cmd(arg=''):
        from ..plugins.manager import PluginManager, PluginError
        pm = getattr(chat, '_plugin_manager', None)
        if pm is None:
            pm = PluginManager(chat.config)
            pm.load()
        parts = arg.strip().split(maxsplit=2)
        if not arg or (parts and parts[0] == 'list'):
            _render_plugins(pm)
            return
        action = parts[0]
        if action in ('enable', 'disable'):
            if len(parts) < 2:
                print(f'Usage: /plugins {action} <name>')
                return
            _toggle_plugin(chat, pm, parts[1], action)
        elif action == 'install':
            _install_plugin(chat, pm, parts[1:])
        elif action == 'update':
            if len(parts) < 2:
                print('Usage: /plugins update <name>')
                return
            _update_plugin(pm, parts[1])
        elif action == 'uninstall':
            if len(parts) < 2:
                print('Usage: /plugins uninstall <name>')
                return
            _uninstall_plugin(chat, pm, parts[1])
        elif pm.get(action):
            _render_plugin_detail(pm, pm.get(action))
        else:
            print(f'Unknown /plugins action or plugin: {action}')
            print('Usage: /plugins [list|enable|disable|install|update|uninstall|<name>]')


def _render_plugins(pm):
    infos = sorted(pm.status(), key=lambda i: i.name)
    if not infos:
        print('  (no plugins installed)')
        print('  Install one from a git URL or local path: /plugins install <source>')
        return
    for info in infos:
        loc = 'global' if info.global_ else 'local'
        parts = [f'{info.name} v{info.version}', loc, info.status]
        if info.error:
            parts.append(info.error)
        if info.requires:
            missing = [p for p, ok in pm.dep_status(info) if not ok]
            if missing:
                parts.append('needs: ' + ', '.join(missing))
        print('  ' + ' — '.join(parts))


def _render_plugin_detail(pm, info):
    print(f'{info.name} v{info.version} ({info.status})')
    print(f'  description: {info.description or "(none)"}')
    print(f'  source: {info.source or "(none)"}')
    print(f'  entry: {info.entry}')
    if info.replio_version:
        print(f'  replio_version: {info.replio_version}')
    if info.python:
        print(f'  python: {info.python}')
    if info.requires:
        print('  requires:')
        for pkg, ok in pm.dep_status(info):
            print(f'    {pkg} — {"installed" if ok else "missing"}')
    provides = info.provides or {}
    for kind in ('tools', 'providers', 'commands'):
        items = provides.get(kind, [])
        if items:
            print(f'  {kind}: ' + ', '.join(items))
    if info.error:
        print(f'  error: {info.error}')


def _toggle_plugin(chat, pm, name, action):
    info = pm.get(name)
    if info is None:
        print(f'Plugin not installed: {name}')
        return
    enabled = list(chat.config.get('plugins.enabled') or [])
    denied = list(chat.config.get('plugins.deny') or [])
    if action == 'enable':
        if name in denied:
            denied.remove(name)
        if enabled and name not in enabled:
            enabled.append(name)
        print(f'Plugin {name} enabled (applies on next start)')
    else:
        if name not in denied:
            denied.append(name)
        print(f'Plugin {name} disabled (applies on next start)')
    chat.config.set('plugins.enabled', enabled)
    chat.config.set('plugins.deny', denied)


def _install_plugin(chat, pm, rest):
    if not rest:
        print('Usage: /plugins install <git-url|path> [--global] [--deps]')
        return
    from ..plugins.manager import PluginError
    source = rest[0]
    global_ = '--global' in rest
    deps = '--deps' in rest
    try:
        info = pm.install(source, global_=global_, deps=deps)
    except PluginError as e:
        print(f'Error installing plugin: {e}')
        return
    print(f'Installed {info.name} v{info.version} — restart to activate')
    if info.status in ('incompatible', 'error', 'disabled'):
        print(f'  {info.status}: {info.error or "not loaded"}')
    if deps and info.requires:
        for pkg in info.requires:
            print(f'  dependency installed: {pkg}')


def _update_plugin(pm, name):
    from ..plugins.manager import PluginError
    try:
        info = pm.update(name)
    except PluginError as e:
        print(f'Error updating plugin: {e}')
        return
    print(f'Updated {info.name} to v{info.version} — restart to apply')


def _uninstall_plugin(chat, pm, name):
    from ..plugins.manager import PluginError
    try:
        pm.uninstall(name)
    except PluginError as e:
        print(f'Error uninstalling plugin: {e}')
        return
    enabled = [n for n in (chat.config.get('plugins.enabled') or []) if n != name]
    denied = [n for n in (chat.config.get('plugins.deny') or []) if n != name]
    chat.config.set('plugins.enabled', enabled)
    chat.config.set('plugins.deny', denied)
    print(f'Uninstalled plugin: {name}')
