import json
import sys
from pathlib import Path

from .config import Config
from .engine import Engine
from .ui import HeadlessUI


def _engine_from_args(args) -> Engine:
    config = Config(path=getattr(args, 'path', None))
    if getattr(args, 'provider', None):
        config.apply('provider', args.provider)
    if getattr(args, 'model', None):
        config.apply('model', args.model)
    if getattr(args, 'base_url', None):
        config.apply('base_url', args.base_url)
    if getattr(args, 'mode', None):
        config.apply('mode', args.mode)
    auto = 'allow' if getattr(args, 'approve', None) is True else 'deny'
    ui = HeadlessUI(auto=auto, verbose=getattr(args, 'verbose', False),
                    stream=getattr(args, 'output', 'json') == 'text',
                    show_thinking=config.get('show_thinking', True),
                    show_thought_duration=config.get('show_thought_duration', True),
                    footer_tokens=config.get('footer_tokens', ['context']))
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
        config.apply('mode', args.mode)
    ui = HeadlessUI(auto='deny', verbose=False, stream=False,
                    show_thinking=config.get('show_thinking', True),
                    footer_tokens=config.get('footer_tokens', ['context']))
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
                    show_thinking=config.get('show_thinking', True),
                    footer_tokens=config.get('footer_tokens', ['context']))
    engine = Engine(config, ui=ui)
    pm = getattr(engine, '_plugin_manager', None)
    service = pm.service('mcp_server') if pm is not None else None
    if service is None:
        print('MCP server unavailable - replio-core-mcp plugin not loaded',
              file=sys.stderr)
        return 1
    service.serve_stdio(engine)
    return 0


def _redact(config: Config, key: str, value) -> str:
    if key == 'api_key' and value:
        return '***'
    return str(value)


def _parse_config_value(value: str | None):
    if value is None:
        return _MISSING_VALUE
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


_MISSING_VALUE = object()


def cmd_config(args) -> int:
    config = Config(path=getattr(args, 'path', None))
    scope = 'global' if getattr(args, 'global_', False) else 'local'
    action = getattr(args, 'action', None)

    if action == 'get':
        keys = getattr(args, 'key', None)
        if not keys:
            keys = list(config.data)
        elif isinstance(keys, str):
            keys = [keys]
        for key in keys:
            val = config.get(key)
            line = f'{key} = {_redact(config, key, val)}'
            if getattr(args, 'show_origin', False):
                line += f'  ({config.origin(key)})'
            print(line)
        return 0

    if action == 'set':
        value = _parse_config_value(args.value)
        if value is _MISSING_VALUE:
            print(f'Error: a value is required to set "{args.key}"', file=sys.stderr)
            return 1
        config.set(args.key, value, scope=scope)
        resolved = 'global' if args.key == 'api_key' else scope
        print(f'{args.key} = {_redact(config, args.key, value)} '
              f'(saved to {resolved} config)')
        return 0

    if action == 'unset':
        config.unset(args.key, scope=scope)
        print(f'Unset {args.key} ({scope} config)')
        return 0

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


def cmd_jobs(args) -> int:
    from .jobs import (Job, JobRegistry, publish, render_list, render_show,
                       render_status, validate_schedule)
    config = Config(path=getattr(args, 'path', None))
    registry = JobRegistry(config.local_path.parent / 'jobs.json')
    action = getattr(args, 'action', None)

    if action == 'list':
        render_list(registry)
        return 0
    if action == 'status':
        render_status(registry)
        return 0
    if action == 'show':
        return 0 if render_show(registry, args.name) else 1
    if action == 'remove':
        if registry.remove(args.name):
            print(f'Removed job: {args.name}')
            return 0
        print(f'Job not found: {args.name}', file=sys.stderr)
        return 1
    if action in ('approve', 'reject', 'enable', 'disable', 'stop'):
        job = registry.find(args.name)
        if job is None:
            print(f'Job not found: {args.name}', file=sys.stderr)
            return 1
        if action == 'approve':
            job.status = 'approved'
            job.enabled = True
            if job.require_approval:
                job.approval_pending = True
        elif action == 'reject':
            job.status = 'proposed'
            job.enabled = False
            job.approval_pending = False
        else:
            job.enabled = False
        registry.save()
        print(f'Job {args.name}: status={job.status}, '
              f'{"enabled" if job.enabled else "disabled"}')
        return 0
    if action == 'add':
        schedule = {}
        if getattr(args, 'cron', None):
            schedule['cron'] = args.cron
        elif getattr(args, 'interval', None):
            schedule['interval'] = args.interval
        elif getattr(args, 'at', None):
            schedule['at'] = args.at
        tool_permission: dict = {}
        for pair in getattr(args, 'tool_permission', []) or []:
            if '=' not in pair:
                print(f'Invalid --tool-permission "{pair}" '
                      '(want category=action)', file=sys.stderr)
                return 1
            category, _, action_name = pair.partition('=')
            tool_permission[category.strip()] = action_name.strip()
        try:
            validate_schedule(schedule)
        except ValueError as e:
            print(f'Error: {e}', file=sys.stderr)
            return 1
        if registry.find(args.name) is not None:
            print(f'Job already exists: {args.name} '
                  '(use `replio jobs show` first)', file=sys.stderr)
            return 1
        require_approval = bool(getattr(args, 'require_approval', False))
        job = Job(
            name=args.name,
            schedule=schedule,
            prompt=args.prompt,
            session=getattr(args, 'session', '') or '',
            mode=getattr(args, 'mode', '') or '',
            provider=getattr(args, 'provider', '') or '',
            model=getattr(args, 'model', '') or '',
            persona=getattr(args, 'persona', '') or '',
            system_prompt=getattr(args, 'system_prompt', '') or '',
            tool_permission=tool_permission,
            tools_deny=list(getattr(args, 'tools_deny', []) or []),
            retries=getattr(args, 'retries', 3),
            backoff=getattr(args, 'backoff', 60.0),
            timeout=getattr(args, 'timeout', 0),
            max_context=getattr(args, 'max_context', 0),
            require_approval=require_approval,
            enabled=args.approval == 'auto',
            status='approved' if args.approval == 'auto' else 'proposed',
        )
        if require_approval:
            job.status = 'waiting_approval'
            job.approval_pending = False
        publish(registry, job)
        return 0
    if action == 'run':
        return _jobs_run(config, registry, args)
    if action == 'daemon':
        from .scheduler import JobScheduler
        scheduler = JobScheduler(config,
                                 verbose=not getattr(args, 'quiet', False))
        return scheduler.daemon(tick_seconds=getattr(args, 'tick', 15.0))
    print('Usage: replio jobs [list|status|show|add|approve|reject|enable|'
          'disable|stop|remove|run|daemon]')
    return 1


def _jobs_run(config, registry, args) -> int:
    from .scheduler import JobScheduler
    job = registry.find(args.name)
    if job is None:
        print(f'Job not found: {args.name}', file=sys.stderr)
        return 1
    verbose = bool(getattr(args, 'verbose', False))
    scheduler = JobScheduler(config, verbose=verbose, stream=verbose)
    original_retries, original_backoff = job.retries, job.backoff
    try:
        if getattr(args, 'no_retry', False):
            job.retries, job.backoff = 0, 0
        run = scheduler.run_job(job)
    finally:
        job.retries, job.backoff = original_retries, original_backoff
        registry.save()
    print(f'Run {job.name}: {run.status} ({run.duration}s)')
    if not verbose and run.content:
        print(run.content)
    if run.reason:
        print(f'  reason: {run.reason}')
    if run.session:
        print(f'  session: {run.session}')
    return 0 if run.status == 'verified' else 1
