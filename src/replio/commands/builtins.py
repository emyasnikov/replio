import os
import sys
import json
from pathlib import Path

from .. import get_version
from ..sessions.render import render_session

SUB_INDENT = 4


def _command_label(name, aliases):
    label = '/' + name
    if aliases:
        label += ', /' + ', /'.join(aliases)
    return label


def _render_commands(registry, names, chat=None):
    metas = {n: registry.meta.get(n, {}) for n in names}
    labels = {n: _command_label(n, metas[n].get('aliases', [])) for n in names}
    max_label = max((len(l) for l in labels.values()), default=0)
    desc_col = 2 + max_label + 2
    for n in names:
        print(f'  {labels[n]:<{desc_col - 2}}{metas[n].get("description", "")}')
        subs = list(metas[n].get('subcommands', []))
        if chat is not None and n == 'tool':
            rows = _tool_rows(chat)
            if rows is None:
                subs.append(('(tool calling disabled)', ''))
            elif not rows:
                subs.append(('(no tools allowed)', ''))
            else:
                subs.extend(rows)
        for sub, sdesc in subs:
            print(f'{" " * SUB_INDENT}{sub:<{desc_col - SUB_INDENT}}{sdesc}')


def _tool_rows(chat):
    chat._init_tooling()
    if not chat._tool_registry or not chat._tool_policy:
        return None
    return [(n, chat._tool_registry.info(n)['short']) for n in sorted(
        n for n in chat._tool_registry.names()
        if chat._tool_policy.allowed(
            n, chat._tool_registry.permission_for(n)))]


def _render_models(models, provider, base_url):
    print(f'{len(models)} models available from {provider} ({base_url}):')
    for m in models:
        print(f'  - {m}')


def _active_model(chat, entry):
    return (entry.provider == chat.config.get('provider')
            and entry.base_url == chat.config.get('base_url')
            and entry.model == chat.config.get('model'))


def _render_known_models(chat):
    entries = chat.models.all()
    if not entries:
        print('No models configured yet - run /connect to add one')
        return
    for group, items in chat.models.grouped():
        print(group + ':')
        for e in items:
            active = '>' if _active_model(chat, e) else ' '
            key = ' (key)' if e.api_key else ''
            print(f'  {active} {e.model}{key}')


def _render_online_models(chat, provider_arg):
    provider = (provider_arg.strip() or chat.config.get('provider')).strip()
    candidates = [e for e in chat.models.all() if e.provider == provider]
    base_url = candidates[0].base_url if candidates else chat.config.get('base_url')
    api_key = next((e.api_key for e in candidates if e.api_key), None)
    model = candidates[0].model if candidates else chat.config.get('model')
    try:
        models, error = chat.list_models(provider=provider, base_url=base_url,
                                         api_key=api_key, model=model)
    except Exception as e:
        models, error = [], str(e)
    if error:
        print(f'[Error] Failed to list models: {error}')
        print(f'  probing {provider} ({base_url}) - run /connect to fix')
        return
    if not models:
        print(f'No models listed from {provider} ({base_url})')
        return
    _render_models(models, provider, base_url)


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
                _render_commands(registry, [canonical], chat)
                return
            chat._init_tooling()
            if chat._tool_registry and chat._tool_registry.info(arg):
                _render_tool_detail(chat, arg)
                return
            print(f'No help available for "{arg}"')
            return
        print('Available commands:')
        _render_commands(registry, sorted(registry.meta), chat)

    @registry.register('exit', aliases=['quit', 'q'], description='Exit the REPL')
    def exit_cmd(_=None):
        chat.session_auto_save()
        sys.exit(0)

    @registry.register('version', aliases=['v'], description='Show the Replio version')
    def version_cmd(_=None):
        print(f'Replio {get_version()}')

    @registry.register('model', description='Show or switch the model; `model list` shows configured models, `model list --online [provider]` probes a provider')
    def model_cmd(arg=''):
        arg = arg.strip()
        if not arg:
            print(f'Current model: {chat.config.get("model")} '
                  f'({chat.config.get("provider")} @ {chat.config.get("base_url")})')
            return
        if arg.startswith('list'):
            rest = arg[len('list'):].strip()
            if not rest:
                _render_known_models(chat)
            elif rest.startswith('--online'):
                _render_online_models(chat, rest[len('--online'):].strip())
            else:
                print('Usage: /model list [--online [provider]]')
            return
        chat.config.set('model', arg)
        chat.provider.model = chat.config.get('model')
        chat.models.touch(chat.config.get('provider'),
                          chat.config.get('base_url'), arg)
        print(f'Model set to: {arg}')

    @registry.register('provider', description='Show or switch the active provider')
    def provider_cmd(arg=''):
        if arg:
            chat.config.set('provider', arg.strip())
            chat._reinit_provider()
            print(f'Provider set to: {chat.config.get("provider")}')
            if chat.config.get('connect_check', True):
                ok, msg, _ = chat.check_connection()
                if not ok:
                    print(f'  Warning: connection test failed - {msg}')
                    print('  Run /connect to fix provider settings')
        else:
            print(f'Current provider: {chat.config.get("provider")}')

    @registry.register('thinking', aliases=['reasoning'],
                       description='Show or toggle streaming of thinking/reasoning tokens')
    def thinking_cmd(arg=''):
        arg = arg.strip().lower()
        current = chat.config.get('show_thinking', False)
        if arg in ('on', '1', 'true', 'yes', 'show'):
            new = True
        elif arg in ('off', '0', 'false', 'no', 'hide'):
            new = False
        elif arg in ('', '?', 'status'):
            new = None
        else:
            print(f"Usage: /thinking [on|off]  (current: {'on' if current else 'off'})")
            return
        if new is None:
            print(f'Thinking streaming: {"on" if current else "off"}')
        else:
            chat.config.set('show_thinking', new)
            print(f'Thinking streaming: {"on" if new else "off"}')

    @registry.register('mode', description='Show or switch the agent mode (plan = read-only, build, or custom)')
    def mode_cmd(arg=''):
        from ..modes import mode_list, resolve_mode
        current, names = resolve_mode(chat.config)
        arg = arg.strip()
        if not arg or arg in ('?', 'status'):
            print(f'Current mode: {current.name}')
            specs = {m.name: m for m in mode_list(chat.config)}
            for m in sorted(specs.values(), key=lambda s: s.name):
                label = '  ' + m.name + ('  <-- current' if m.name == current.name else '')
                print(f'{label}')
                if m.instruction:
                    print(f'    {m.instruction.splitlines()[0][:80]}')
            return
        if arg not in names:
            print(f'Unknown mode "{arg}" - valid modes: ' + ', '.join(names))
            return
        chat.config.set('mode', arg)
        print(f'Mode set to: {arg}')
        if arg == 'plan':
            print('  Read-only: write and exec tools are disabled')

    @registry.register('models', aliases=['model-list'],
                       description='List models available from the connected provider')
    def models_cmd(_=None):
        provider = chat.config.get('provider')
        base_url = chat.config.get('base_url')
        try:
            models, error = chat.list_models()
        except Exception as e:
            models, error = [], str(e)
        if error:
            print(f'[Error] Failed to list models: {error}')
            print(f'  probing {provider} ({base_url}) - run /connect to fix')
            return
        if not models:
            print(f'No models listed from {provider} ({base_url})')
            return
        _render_models(models, provider, base_url)
        model = chat.config.get('model')
        if model and model not in models:
            print(f'  (configured model "{model}" not in the model list)')

    @registry.register('persona', description='Manage personas', subcommands=[
        ('list', 'List personas (list <tag> filters by tag)'),
        ('show', 'Show a persona definition'),
        ('new', 'Create or override a persona (local)'),
        ('remove', 'Remove a persona'),
    ])
    def persona_cmd(arg=''):
        from ..personas import Persona
        pr = chat.personas
        parts = arg.strip().split(maxsplit=1)
        action = parts[0] if parts else ''
        if not action or action == 'list':
            tag = ''
            if action == 'list' and len(parts) > 1:
                tag = parts[1].strip()
            personas = pr.all()
            if tag:
                personas = [p for p in personas if tag in p.tags]
            if not personas:
                if tag:
                    print(f'  (no personas tagged "{tag}")')
                    known = ', '.join(sorted({t for p in pr.all()
                                              for t in p.tags}))
                    if known:
                        print(f'  known tags: {known}')
                else:
                    print('  (no personas configured)')
                    print('  Create one with /persona new <name>, or edit '
                          f'{pr.local_path}')
                return
            label = f' tagged "{tag}"' if tag else ''
            print(f'{len(personas)} personas{label}:')
            for p in personas:
                model = f' [{p.model}]' if p.model else ''
                tags = f' tags={",".join(p.tags)}' if p.tags else ''
                origin = f' ({pr.origin(p.name)})'
                print(f'  - {p.name}{model}{tags}{origin}')
            return
        if action == 'show':
            name = parts[1].strip() if len(parts) > 1 else ''
            if not name:
                print('Usage: /persona show <name>')
                return
            p = pr.find(name)
            if p is None:
                print(f'Persona not found: {name}')
                return
            print(f'{p.name} ({pr.origin(p.name)})')
            print(f'  system_prompt: {p.system_prompt or "(empty)"}')
            if p.tags:
                print(f'  tags: {", ".join(p.tags)}')
            if p.model:
                print(f'  model: {p.model}')
            if p.skills:
                print(f'  skills: {", ".join(p.skills)}')
            if p.tool_permission:
                print('  tool_permission: '
                      + json.dumps(p.tool_permission))
            return
        if action == 'new':
            rest = parts[1].strip() if len(parts) > 1 else ''
            if not rest:
                print('Usage: /persona new <name> [system prompt]')
                return
            name = rest.split(maxsplit=1)[0]
            prompt = rest[len(name):].strip()
            existing = pr.find(name)
            prev_origin = pr.origin(name)
            pr.put(Persona(name=name, system_prompt=prompt), scope='local')
            if existing is not None:
                print(f'Overrode persona: {name} (was {prev_origin}) - '
                      f'edit {pr.local_path}')
            else:
                print(f'Created persona: {name} (local) - edit {pr.local_path}')
            return
        if action == 'remove':
            name = parts[1].strip() if len(parts) > 1 else ''
            if not name:
                print('Usage: /persona remove <name>')
                return
            if pr.remove(name):
                print(f'Removed persona: {name} (local)')
            elif pr.is_bundled(name):
                print(f'{name} is bundled with replio - override it with '
                      '/persona new <name>, or edit the local personas file, '
                      'instead of removing')
            else:
                print(f'No local persona to remove: {name}')
            return
        print('Usage: /persona [list|show <name>|new <name> [prompt]|remove <name>]')

    @registry.register('connect', description='Set up provider connection interactively')
    def connect_cmd(_=None):
        from ..providers import PROVIDERS, detect_provider
        providers = dict(PROVIDERS)
        pm = getattr(chat, '_plugin_manager', None)
        if pm is not None:
            providers.update(pm.provider_classes())
        registry = chat.models
        known = registry.all()
        fresh = (chat.config.get('provider') == 'ollama'
                 and chat.config.get('base_url') == 'https://api.ollama.com'
                 and chat.config.get('model') == 'llama3.2')
        if known and fresh:
            print('Known models (global):')
            for i, e in enumerate(known, 1):
                key = ' (key)' if e.api_key else ''
                print(f'  {i}. [{e.provider}] {e.model} - {e.base_url}{key}')
        print('Setting up provider connection:')
        provider = input(
            f'  Provider [{chat.config.get("provider")}]: '
        ).strip() or chat.config.get('provider')
        base_url = input(
            f'  Base URL [{chat.config.get("base_url")}]: '
        ).strip() or chat.config.get('base_url')
        model = input(
            f'  Model [{chat.config.get("model")}]: '
        ).strip() or chat.config.get('model')
        picked = None
        if model.startswith('#'):
            try:
                picked = known[int(model[1:]) - 1]
            except (ValueError, IndexError):
                print(f'  Unknown model number "{model}"')
                return
            provider, base_url, model = picked.provider, picked.base_url, picked.model
        api_key = ''
        if picked is not None:
            print(f'  API key: stored key {picked.api_key and "(present)" or "(missing)"}')
            api_key = input('  API key [<stored>]: ').strip() or picked.api_key
        else:
            api_key = input('  API key (leave empty to skip): ').strip()

        detected = detect_provider(base_url)
        if detected in providers and detected != 'openai-compatible' and detected != provider:
            print(f'  Detected provider "{detected}" from base URL - switching')
            provider = detected

        checkout = chat.config.get('connect_check', True)
        if checkout:
            ok, msg, models = chat.check_connection(
                base_url=base_url, api_key=api_key, model=model, provider=provider)
            if not ok:
                print(f'  [Error] Connection test failed: {msg}')
                try:
                    answer = input('  Save anyway? [y/N] ').strip().lower()
                except (EOFError, KeyboardInterrupt):
                    print()
                    return
                if answer not in ('y', 'yes'):
                    print('  Connection not saved - run /connect again with corrected values')
                    return

        was_known = registry.find(provider, base_url, model) is not None
        registry.put(provider, base_url, model, api_key)
        chat.config.set('base_url', base_url)
        chat.config.set('provider', provider)
        chat.config.set('model', model)

        chat._reinit_provider()
        verb = 'Updated' if was_known else 'Added'
        if checkout:
            print(f'Connected to {provider} ({base_url}) - {msg}')
        else:
            print(f'Connected to {provider} ({base_url})')
        print(f'  {verb} to global model list: {provider} ({base_url}) - {model}')
        if checkout:
            if model and models and model not in models:
                try:
                    answer = input('  Show available models? [y/N] ').strip().lower()
                except (EOFError, KeyboardInterrupt):
                    print()
                    return
                if answer in ('y', 'yes'):
                    _render_models(models, provider, base_url)

    @registry.register('config', description='Show, get, set, or unset config values (--global for the global config)')
    def config_cmd(arg=''):
        scope = 'local'
        text = arg.strip()
        while text.startswith('--global') or text.startswith('--local'):
            scope = 'global' if text.startswith('--global') else 'local'
            flag_len = len('--global') if text.startswith('--global') else len('--local')
            text = text[flag_len:].lstrip()
        parts = text.split(maxsplit=1)
        if not text:
            for k, v in chat.config.data.items():
                print(f'  {k}: {v}  ({chat.config.origin(k)})')
            return
        key = parts[0]
        rest = parts[1].strip() if len(parts) > 1 else ''

        if key == 'reload' and not rest:
            old = {k: chat.config.get(k) for k in ('provider', 'base_url', 'model')}
            chat.config.reload()
            print('Config reloaded from disk')
            for k in ('provider', 'base_url', 'model'):
                if chat.config.get(k) != old[k]:
                    print(f'  {k}: {old[k]} → {chat.config.get(k)} - run /provider or /connect to apply')
            return

        if key == 'unset' and rest:
            k = rest.split(maxsplit=1)[0]
            chat.config.unset(k, scope=scope)
            print(f'Unset {k} ({scope} config)')
            return

        if not rest:
            val = chat.config.get(key)
            print(f'  {key}: {val}  ({chat.config.origin(key)})')
            return

        if rest in ('-a', '-r') or rest.startswith('-a ') or rest.startswith('-r '):
            op = rest[:2]
            items = rest[2:].strip().split()
            current = chat.config.get(key)
            if not isinstance(current, list):
                print(f'Config {key} is not a list - cannot add/remove items')
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
                chat.config.set(key, current, scope=scope)
                print(f'Config {key} = {current} ({scope})')
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
        chat.config.set(key, value, scope=scope)
        print(f'Config {key} = {value} ({scope})')

    @registry.register('session', description='Manage saved sessions', subcommands=[
        ('new', 'Start a new session'),
        ('list', 'List saved sessions'),
        ('preview', 'Show a structural preview of a session'),
        ('load', 'Load a session'),
        ('delete', 'Delete a session'),
        ('save', 'Save the current session'),
        ('export', 'Export a session to Markdown'),
    ])
    def session_cmd(arg=''):
        parts = arg.strip().split(maxsplit=2)
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
                    child = ''
                    if s.startswith('sub_'):
                        data = chat.sessions.read(s)
                        if data and getattr(data, 'parent_id', ''):
                            child = f'  (child of {data.parent_id})'
                    print(f'  {s}{marker}{child}')
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
                print(f'Loaded session: {name} - {n} messages · '
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
        elif action == 'export':
            name = parts[1] if len(parts) > 1 else ''
            out = parts[2] if len(parts) > 2 else ''
            if not name:
                print('Usage: /session export <name> [out]')
                return
            s = chat.sessions.read(name)
            if s is None:
                print(f'Session not found: {name}')
                return
            markdown = render_session(s)
            if out == '-':
                sys.stdout.write(markdown)
                return
            if out:
                path = Path(out)
            else:
                path = chat.sessions.sessions_dir.parent / 'exports' / f'{name}.md'
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(markdown)
            print(f'Exported session: {name} -> {path}')

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
            rows = _tool_rows(chat)
            if rows is None:
                print('Tool calling is disabled (tool_calling: false)')
                return
            if not rows:
                print('No tools allowed')
                return
            print('Available tools:')
            name_w = max(len(n) for n, _ in rows)
            for n, tdesc in rows:
                print(f'  {n:<{name_w + 2}}{tdesc}')
            print('Use /help <tool> for details')
            return
        name = parts[0]
        args_str = parts[1] if len(parts) > 1 else '{}'
        try:
            arguments = json.loads(args_str) if args_str else {}
        except json.JSONDecodeError:
            print('Usage: /tool <name> {"key": "value"}')
            return
        print(chat._run_tool(name, arguments, echo=False))

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
            _update_plugin(chat, pm, parts[1])
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

    @registry.register('jobs', description='Manage scheduled and durable jobs', subcommands=[
        ('list', 'List configured jobs'),
        ('status', 'Runtime summary per job (fired count, last error, uptime)'),
        ('show', 'Show a job and its run history'),
        ('add', 'Add a job (starts proposed, approve to activate)'),
        ('approve', 'Approve a job so it runs on schedule'),
        ('reject', 'Reject a proposed job'),
        ('enable', 'Enable a disabled job'),
        ('disable', 'Disable a job'),
        ('stop', 'Stop a job - same as disable'),
        ('edit', 'Open the job task file in $EDITOR (creates the template first)'),
        ('remove', 'Remove a job definition'),
        ('run', 'Run a job now'),
    ])
    def jobs_cmd(arg=''):
        from ..jobs import (Job, JobRegistry, publish, render_list, render_show,
                            render_status, validate_schedule)
        import shlex
        registry = JobRegistry(chat.config.local_path.parent / 'jobs.json')
        tokens = shlex.split(arg)
        action = tokens[0] if tokens else 'list'
        if action in ('list', 'status'):
            (render_status if action == 'status' else render_list)(registry)
            return
        if action == 'show':
            name = tokens[1] if len(tokens) > 1 else ''
            if not name:
                print('Usage: /jobs show <name>')
                return
            render_show(registry, name)
            return
        if action == 'remove':
            name = tokens[1] if len(tokens) > 1 else ''
            if not name:
                print('Usage: /jobs remove <name>')
                return
            if registry.remove(name):
                print(f'Removed job: {name}')
            else:
                print(f'Job not found: {name}')
            return
        if action in ('approve', 'reject', 'enable', 'disable', 'stop'):
            name = tokens[1] if len(tokens) > 1 else ''
            job = registry.find(name) if name else None
            if job is None:
                print(f'Usage: /jobs {action} <name>')
                return
            if action == 'approve':
                job.status = 'approved'
                job.enabled = True
                if job.require_approval:
                    job.approval_pending = True
            elif action == 'reject':
                job.status = 'proposed'
                job.enabled = False
                job.approval_pending = False
            elif action == 'enable':
                job.enabled = True
            else:
                job.enabled = False
            registry.save()
            print(f'Job {name}: status={job.status}, '
                  f'{"enabled" if job.enabled else "disabled"}')
            return
        if action == 'run':
            from ..scheduler import JobScheduler
            name = tokens[1] if len(tokens) > 1 else ''
            job = registry.find(name) if name else None
            if job is None:
                print('Usage: /jobs run <name>')
                return
            run = JobScheduler(chat.config, verbose=False).run_job(job)
            print(f'Run {job.name}: {run.status} ({run.duration}s)')
            if run.content:
                print(run.content)
            if run.reason:
                print(f'  reason: {run.reason}')
            if run.session:
                print(f'  session: {run.session}')
            return
        if action == 'add':
            if len(tokens) < 2:
                print('Usage: /jobs add <name> --cron "0 2 * * *" '
                      '[--prompt "text"|--file path] '
                      '[--interval N|--at ISO] [--approval auto]')
                return
            name = tokens[1]
            opts, after = {}, []
            i = 2
            while i < len(tokens):
                tok = tokens[i]
                if tok in ('--cron', '--interval', '--at', '--prompt', '--file',
                           '--session', '--mode', '--provider', '--model', '--persona'):
                    opts[tok] = tokens[i + 1] if i + 1 < len(tokens) else ''
                    i += 2
                elif tok == '--approval':
                    opts[tok] = tokens[i + 1].lower() if i + 1 < len(tokens) else 'manual'
                    i += 2
                else:
                    after.append(tok)
                    i += 1
            prompt = opts.get('--prompt', '') or ''
            file_arg = opts.get('--file', '') or ''
            if not prompt and not file_arg:
                print('Usage: /jobs add <name> --prompt "text" --file path '
                      '(one of them required)')
                return
            schedule: dict = {}
            if opts.get('--cron'):
                schedule['cron'] = opts['--cron']
            elif opts.get('--interval'):
                try:
                    schedule['interval'] = int(opts['--interval'])
                except ValueError:
                    print('Invalid --interval value')
                    return
            elif opts.get('--at'):
                schedule['at'] = opts['--at']
            else:
                print('One of --cron, --interval, or --at is required')
                return
            try:
                validate_schedule(schedule)
            except ValueError as e:
                print(f'Error: {e}')
                return
            existing = registry.find(name)
            if existing is not None:
                print(f'Job already exists: {name}')
                return
            from ..cli import _store_task_file
            from ..jobs import ensure_task_file
            worktree = chat.config.local_path.parent.parent
            task_file = _store_task_file(worktree, file_arg)
            auto = opts.get('--approval') == 'auto'
            job = Job(
                name=name,
                schedule=schedule,
                prompt=prompt,
                session=opts.get('--session', '') or '',
                mode=opts.get('--mode', '') or '',
                provider=opts.get('--provider', '') or '',
                model=opts.get('--model', '') or '',
                persona=opts.get('--persona', '') or '',
                task_file=task_file,
                enabled=auto,
                status='approved' if auto else 'proposed',
            )
            if job.task_file:
                ensure_task_file(worktree, job)
            publish(registry, job)
            return
        if action == 'edit':
            name = tokens[1] if len(tokens) > 1 else ''
            job = registry.find(name) if name else None
            if job is None:
                print('Usage: /jobs edit <name>')
                return
            from ..jobs import ensure_task_file
            path = ensure_task_file(chat.config.local_path.parent.parent, job)
            editor = os.environ.get('EDITOR') or os.environ.get('VISUAL') or 'vi'
            import shlex
            import subprocess
            subprocess.call(shlex.split(editor) + [str(path)])
            return
        print('Usage: /jobs [list|status|show <name>|add <name> ...|approve <name>|'
              'reject <name>|enable <name>|disable <name>|stop <name>|'
              'edit <name>|remove <name>|run <name>]')


def _render_plugins(pm):
    infos = sorted(pm.status(), key=lambda i: i.name)
    if not infos:
        print('  (no plugins installed)')
        print('  Install one from a git URL or local path: /plugins install <source>')
        return
    for info in infos:
        parts = [f'{info.name} v{info.version}', info.origin, info.status]
        if info.error:
            parts.append(info.error)
        if info.requires:
            missing = [p for p, ok in pm.dep_status(info) if not ok]
            if missing:
                parts.append('needs: ' + ', '.join(missing))
        print('  ' + ' - '.join(parts))


def _render_plugin_detail(pm, info):
    print(f'{info.name} v{info.version} ({info.status})')
    print(f'  origin: {info.origin}')
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
            print(f'    {pkg} - {"installed" if ok else "missing"}')
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
    plugins = [str(n) for n in (chat.config.get('plugins') or [])]
    if action == 'enable':
        if name not in plugins:
            plugins.append(name)
        print(f'Plugin {name} enabled (applies on next start)')
    else:
        if name in plugins:
            plugins.remove(name)
        print(f'Plugin {name} disabled (applies on next start)')
    chat.config.set('plugins', plugins)


def _refresh_personas(chat, pm):
    personas = getattr(chat, 'personas', None)
    if personas is not None:
        personas.reload(pm)


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
    plugins = [str(n) for n in (chat.config.get('plugins') or [])]
    if info.name not in plugins:
        plugins.append(info.name)
        chat.config.set('plugins', plugins)
    _refresh_personas(chat, pm)
    print(f'Installed {info.name} v{info.version} - restart to activate')
    if info.status in ('incompatible', 'error', 'disabled'):
        print(f'  {info.status}: {info.error or "not loaded"}')
    if deps and info.requires:
        for pkg in info.requires:
            print(f'  dependency installed: {pkg}')


def _update_plugin(chat, pm, name):
    from ..plugins.manager import PluginError
    try:
        info = pm.update(name)
    except PluginError as e:
        print(f'Error updating plugin: {e}')
        return
    _refresh_personas(chat, pm)
    print(f'Updated {info.name} to v{info.version} - restart to apply')


def _uninstall_plugin(chat, pm, name):
    from ..plugins.manager import PluginError
    try:
        pm.uninstall(name)
    except PluginError as e:
        print(f'Error uninstalling plugin: {e}')
        return
    plugins = [n for n in (chat.config.get('plugins') or []) if n != name]
    chat.config.set('plugins', plugins)
    _refresh_personas(chat, pm)
    print(f'Uninstalled plugin: {name}')
