import json
import sys
from pathlib import Path

from .config import Config
from .engine import Engine
from .ui import HeadlessUI


def _engine_from_args(args) -> Engine:
    config = Config(path=getattr(args, 'path', None))
    if getattr(args, 'provider', None):
        config.set('provider', args.provider)
    if getattr(args, 'model', None):
        config.set('model', args.model)
    if getattr(args, 'base_url', None):
        config.set('base_url', args.base_url)
    if getattr(args, 'mode', None):
        config.set('mode', args.mode)
    auto = 'allow' if getattr(args, 'approve', None) is True else 'deny'
    ui = HeadlessUI(auto=auto, verbose=getattr(args, 'verbose', False),
                    stream=getattr(args, 'output', 'json') == 'text',
                    show_thinking=config.get('show_thinking', True))
    return Engine(config, ui=ui)


def cmd_run(args) -> int:
    engine = _engine_from_args(args)
    engine.load_or_create_session(getattr(args, 'session_id', None))
    result = engine.chat(args.prompt, autoname=getattr(args, 'session_id', None) is None)
    if args.output == 'json':
        sys.stdout.write(json.dumps(result.to_dict(), indent=2) + '\n')
    return 0 if result.status in ('ok', 'truncated') else 1


def cmd_export(args) -> int:
    from .sessions.manager import SessionManager
    from .sessions.render import render_session
    config = Config(path=getattr(args, 'path', None))
    sessions = SessionManager(config.local_path.parent / 'sessions')
    session = sessions.read(args.name)
    if session is None:
        print(f'Session not found: {args.name}', file=sys.stderr)
        return 1
    markdown = render_session(session)
    out = getattr(args, 'out', None)
    if out == '-':
        sys.stdout.write(markdown)
        return 0
    if out:
        path = Path(out)
    else:
        path = sessions.sessions_dir.parent / 'exports' / f'{args.name}.md'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown)
    print(f'Exported session: {args.name} -> {path}')
    return 0


def cmd_models(args) -> int:
    from .ui import NullUI
    config = Config(path=getattr(args, 'path', None))
    engine = Engine(config, ui=NullUI())
    models, error = engine.list_models()
    if error:
        print(f'Error: {error}', file=sys.stderr)
        return 1
    provider = config.get('provider')
    base_url = config.get('base_url')
    if not models:
        print(f'No models listed from {provider} ({base_url})')
        return 0
    print(f'{len(models)} models available from {provider} ({base_url}):')
    for m in models:
        print(f'  - {m}')
    return 0


def cmd_serve(args) -> int:
    from .server import HeadlessServer, ChatHandler
    config = Config(path=args.path)
    if getattr(args, 'mode', None):
        config.set('mode', args.mode)
    ui = HeadlessUI(auto='deny', verbose=False, stream=False,
                    show_thinking=config.get('show_thinking', True))
    engine = Engine(config, ui=ui)
    pm = getattr(engine, '_plugin_manager', None)
    mcp_service = pm.service('mcp_server') if pm is not None else None
    server = HeadlessServer((args.host, args.port), ChatHandler,
                            engine=engine, mcp_service=mcp_service)
    print(f'replio serve ({config.get("mode")} mode) - http://{args.host}:{args.port} '
          f'(POST /chat, GET /sessions, GET /health, GET /version'
          f'{", POST /mcp" if mcp_service else ""})', file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def cmd_mcp(args) -> int:
    config = Config(path=args.path)
    ui = HeadlessUI(auto='deny', verbose=False, stream=False,
                    show_thinking=config.get('show_thinking', True))
    engine = Engine(config, ui=ui)
    pm = getattr(engine, '_plugin_manager', None)
    service = pm.service('mcp_server') if pm is not None else None
    if service is None:
        print('MCP server unavailable - replio-core-mcp plugin not loaded',
              file=sys.stderr)
        return 1
    service.serve_stdio(engine)
    return 0


def cmd_plugins(args) -> int:
    from .plugins.manager import PluginManager, PluginError
    config = Config(path=getattr(args, 'path', None))
    pm = PluginManager(config)
    pm.load()
    if args.action == 'list':
        infos = sorted(pm.status(), key=lambda i: i.name)
        if not infos:
            print('(no plugins installed)')
            return 0
        for info in infos:
            parts = [f'{info.name} v{info.version}', info.origin, info.status]
            if info.error:
                parts.append(info.error)
            missing = [p for p, ok in pm.dep_status(info) if not ok]
            if missing:
                parts.append('needs: ' + ', '.join(missing))
            print('  ' + ' - '.join(parts))
        return 0
    try:
        if args.action == 'install':
            info = pm.install(args.source, global_=getattr(args, 'global_', False),
                              deps=getattr(args, 'deps', False))
            plugins = [str(n) for n in (config.get('plugins') or [])]
            if info.name not in plugins:
                plugins.append(info.name)
                config.set('plugins', plugins)
            print(f'Installed {info.name} v{info.version} ({info.status})')
            if info.status in ('incompatible', 'error', 'disabled'):
                print(f'{info.status}: {info.error or "not loaded"}', file=sys.stderr)
        elif args.action == 'update':
            info = pm.update(args.name)
            print(f'Updated {info.name} to v{info.version} ({info.status})')
        elif args.action == 'uninstall':
            pm.uninstall(args.name)
            plugins = [n for n in (config.get('plugins') or []) if n != args.name]
            config.set('plugins', plugins)
            print(f'Uninstalled plugin: {args.name}')
    except PluginError as e:
        print(f'Error: {e}', file=sys.stderr)
        return 1
    return 0
