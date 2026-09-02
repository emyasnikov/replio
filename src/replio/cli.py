from __future__ import annotations

import json
import os
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


def cmd_eval(args) -> int:
    import json as _json
    from .eval import (discover_eval, format_compare, format_results,
                       run_compare, run_suite, select_fixtures)
    source = Config(path=getattr(args, 'path', None))
    fixtures = discover_eval(source)
    if getattr(args, 'action', None) == 'list':
        if not fixtures:
            print('No eval fixtures found.')
            return 0
        for fid in sorted(fixtures):
            fixture = fixtures[fid]
            expected = ', '.join(fixture.expected) if fixture.expected else 'any'
            label = fixture.description or fixture.task
            print(f'{fid} - {label[:60]} (expected: {expected})')
        return 0
    selected = select_fixtures(fixtures, getattr(args, 'fixture', None))
    if not selected:
        print('No eval fixtures found.', file=sys.stderr)
        return 1
    if getattr(args, 'compare', None):
        providers = [p.strip() for p in args.compare.split(',') if p.strip()]
        rows = run_compare(selected, source, providers,
                           getattr(args, 'model', None) or '')
        if args.output == 'json':
            sys.stdout.write(_json.dumps(
                {row['provider']: row['summary'] for row in rows}, indent=2) + '\n')
        else:
            sys.stdout.write(format_compare(rows) + '\n')
        return 0
    overrides = {}
    if getattr(args, 'provider', None):
        overrides['provider'] = args.provider
    if getattr(args, 'model', None):
        overrides['model'] = args.model
    if getattr(args, 'base_url', None):
        overrides['base_url'] = args.base_url
    results, summary = run_suite(selected, source, overrides)
    if args.output == 'json':
        sys.stdout.write(_json.dumps(
            {'summary': summary, 'results': results}, indent=2) + '\n')
    else:
        sys.stdout.write(format_results(results, summary) + '\n')
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
            line = f'{key} = {config.get(key)}'
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
        print(f'{args.key} = {value} (saved to {scope} config)')
        return 0

    if action == 'unset':
        config.unset(args.key, scope=scope)
        print(f'Unset {args.key} ({scope} config)')
        return 0

    return 0


def cmd_plugins(args) -> int:
    from .plugins.manager import PluginManager, PluginError, load_plugin_test_suite
    config = Config(path=getattr(args, 'path', None))
    pm = PluginManager(config)
    pm.load()
    if args.action == 'test':
        return _plugins_run_tests(pm, args)
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


def _plugins_run_tests(pm, args) -> int:
    import unittest

    from .plugins.manager import load_plugin_test_suite

    name = getattr(args, 'name', None)
    infos = [pm.get(name)] if name else [i for i in pm.status()]
    if name and infos[0] is None:
        print(f'Plugin not found: {name}', file=sys.stderr)
        return 1
    failed = False
    for info in infos:
        suite = load_plugin_test_suite(info.directory)
        count = suite.countTestCases()
        if name and count == 0:
            print(f'Plugin has no test suite: {info.name}', file=sys.stderr)
            return 1
        if count == 0:
            continue
        print(f'Running {info.name} tests ({count})...')
        result = unittest.TextTestRunner(
            stream=sys.stderr, verbosity=2 if getattr(args, 'verbose', False) else 1,
        ).run(suite)
        failed = failed or not result.wasSuccessful()
    return 1 if failed else 0


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
        file_arg = getattr(args, 'file', None) or ''
        prompt = getattr(args, 'prompt', '') or ''
        if not prompt and not file_arg:
            print('Error: a --prompt or --file is required', file=sys.stderr)
            return 1
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
            prompt=prompt,
            session=getattr(args, 'session', '') or '',
            mode=getattr(args, 'mode', '') or '',
            provider=getattr(args, 'provider', '') or '',
            model=getattr(args, 'model', '') or '',
            persona=getattr(args, 'persona', '') or '',
            system_prompt=getattr(args, 'system_prompt', '') or '',
            task_file=_store_task_file(config.local_path.parent.parent, file_arg),
            tool_permission=tool_permission,
            tools_deny=list(getattr(args, 'tools_deny', []) or []),
            retries=getattr(args, 'retries', 3),
            backoff=getattr(args, 'backoff', 60.0),
            timeout=getattr(args, 'timeout', 0),
            require_approval=require_approval,
            enabled=args.approval == 'auto',
            status='approved' if args.approval == 'auto' else 'proposed',
        )
        if require_approval:
            job.status = 'waiting_approval'
            job.approval_pending = False
        if job.task_file:
            from .jobs import ensure_task_file
            ensure_task_file(config.local_path.parent.parent, job)
        publish(registry, job)
        return 0
    if action == 'edit':
        job = registry.find(args.name)
        if job is None:
            print(f'Job not found: {args.name}', file=sys.stderr)
            return 1
        from .jobs import ensure_task_file
        path = ensure_task_file(config.local_path.parent.parent, job)
        editor = os.environ.get('EDITOR') or os.environ.get('VISUAL') or 'vi'
        import shlex
        import subprocess
        try:
            code = subprocess.call(shlex.split(editor) + [str(path)])
        except OSError as e:
            print(f'Error opening editor "{editor}": {e}', file=sys.stderr)
            return 1
        return 0 if code == 0 else 1
    if action == 'run':
        return _jobs_run(config, registry, args)
    if action == 'daemon':
        from .scheduler import JobScheduler
        scheduler = JobScheduler(config,
                                 verbose=not getattr(args, 'quiet', False))
        return scheduler.daemon(tick_seconds=getattr(args, 'tick', 15.0))
    print('Usage: replio jobs [list|status|show|add|approve|reject|enable|'
          'disable|stop|edit|remove|run|daemon]')
    return 1


def _store_task_file(worktree: Path, value: str) -> str:
    if not value:
        return ''
    path = Path(value)
    if not path.is_absolute():
        path = (Path(worktree) / path).resolve()
    try:
        return str(path.relative_to(Path(worktree)))
    except ValueError:
        return str(path)


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


def _fleet_root(args) -> Path:
    path = getattr(args, 'path', None)
    return (Path(path) if path else Path.cwd()).resolve()


def _fleet_controller(args) -> FleetController:
    from .fleet import FleetController
    return FleetController(_fleet_root(args))


def cmd_fleet(args) -> int:
    from .fleet import AgentDef, _now
    controller = _fleet_controller(args)
    action = getattr(args, 'action', None)

    if action == 'init':
        added = []
        for entry in sorted(controller.root.iterdir()):
            if not entry.is_dir():
                continue
            if (entry / '.replio' / 'config.json').exists():
                if controller.manifest.find(entry.name) is None:
                    controller.manifest.add(AgentDef(
                        name=entry.name, dir=str(entry.resolve()), added_at=_now()))
                    added.append(entry.name)
        if added:
            print(f'Discovered {len(added)} agent(s): {", ".join(added)}')
        else:
            print('No new agents found (subdirectories holding .replio/config.json)')
        return 0

    if action == 'add':
        if controller.manifest.find(args.name) is not None:
            print(f'Agent already exists: {args.name}', file=sys.stderr)
            return 1
        agent_dir = (Path(args.dir).resolve() if getattr(args, 'dir', '')
                     else (controller.root / args.name).resolve())
        controller.manifest.add(AgentDef(
            name=args.name, dir=str(agent_dir),
            prefer_port=int(getattr(args, 'port', 0) or 0),
            max_restarts=int(getattr(args, 'max_restarts', 10) or 0),
            added_at=_now()))
        print(f'Added agent: {args.name} -> {agent_dir}')
        print('  Run `replio fleet config <name>` to generate its config, '
              'then `replio fleet up` to start it')
        return 0

    if action == 'remove':
        if controller.manifest.find(args.name) is None:
            print(f'Agent not found: {args.name}', file=sys.stderr)
            return 1
        controller.stop_agent(args.name)
        controller.manifest.remove(args.name)
        print(f'Removed agent: {args.name}')
        return 0

    if action == 'up':
        if getattr(args, 'daemon_', False):
            return controller.daemon()
        if getattr(args, 'detach', False):
            return _fleet_detach(controller)
        return controller.run()

    if action == 'down':
        controller.down()
        print(f'Fleet stopped ({controller.root})')
        return 0

    if action == 'status':
        return _fleet_status(controller)

    if action == 'restart':
        names = [args.name] if getattr(args, 'name', None) else None
        if names and controller.manifest.find(names[0]) is None:
            print(f'Agent not found: {names[0]}', file=sys.stderr)
            return 1
        restarted = controller.restart(names)
        label = ', '.join(restarted) if restarted else '(none running)'
        print(f'Stopped for restart: {label}')
        if restarted:
            print('  Agents relaunch on the next supervisor sweep '
                  '(or run `replio fleet up`)')
        return 0

    if action == 'logs':
        return _fleet_logs(controller, args)

    if action == 'config':
        return _fleet_config(controller, args)

    print('Usage: replio fleet '
          '[init|add|remove|up|down|status|restart|logs|config]')
    return 1


def _fleet_detach(controller) -> int:
    import subprocess
    log_dir = controller.root / '.replio' / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / 'fleet.log'
    handle = open(log_path, 'ab')
    cmd = [sys.executable, '-m', 'replio', 'fleet', '--path', str(controller.root),
           'up', '--daemon']
    try:
        proc = subprocess.Popen(cmd, stdout=handle, stderr=subprocess.STDOUT,
                                cwd=str(controller.root), start_new_session=True)
    finally:
        handle.close()
    print(f'Fleet supervisor detached (pid {proc.pid}, log {log_path})')
    return 0


def _fleet_status(controller) -> int:
    rows = controller.status_rows()
    if not rows:
        print(f'No agents in the manifest ({controller.root}) - '
              'run `replio fleet init` or `replio fleet add`')
        return 0
    headers = ('AGENT', 'ENABLED', 'PORT', 'PID', 'STATE', 'RESTARTS', 'LAST ERROR')
    cells = []
    for r in rows:
        budget = f"{r['max_restarts']}" if r['max_restarts'] else 'unlim'
        cells.append([
            r['name'],
            'yes' if r['enabled'] else 'no',
            str(r['port'] or '-'),
            str(r['pid'] or '-'),
            r['state'],
            f"{r['restarts']}/{budget}",
            r['last_error'] or '',
        ])
    widths = [len(h) for h in headers]
    for c in cells:
        for i, value in enumerate(c):
            widths[i] = max(widths[i], len(value))
    fmt = '  '.join('{:<%d}' % w for w in widths)
    print(fmt.format(*headers))
    for c in cells:
        print(fmt.format(*c))
    return 0


def _fleet_logs(controller, args) -> int:
    import time
    agent = controller.manifest.find(args.name)
    if agent is None:
        print(f'Agent not found: {args.name}', file=sys.stderr)
        return 1
    log_path = controller.log_path(agent)
    if not log_path.exists():
        print(f'No log yet: {log_path}', file=sys.stderr)
        return 1
    n = max(1, int(getattr(args, 'n', 50) or 50))
    if getattr(args, 'follow', False):
        size = log_path.stat().st_size
        with open(log_path) as f:
            f.seek(size)
            try:
                while True:
                    line = f.readline()
                    if line:
                        print(line, end='')
                    else:
                        time.sleep(0.25)
            except KeyboardInterrupt:
                pass
        return 0
    lines = log_path.read_text().splitlines()
    if not lines:
        print(f'(empty log) {log_path}')
        return 0
    for line in lines[-n:]:
        print(line)
    return 0


def _fleet_config(controller, args) -> int:
    import json
    from .personas import PersonaRegistry
    agent = controller.manifest.find(args.name)
    if agent is None:
        print(f'Agent not found: {args.name}', file=sys.stderr)
        return 1
    agent_dir = controller.agent_dir(agent)
    patch: dict = {}
    if getattr(args, 'provider', ''):
        patch['provider'] = args.provider
    if getattr(args, 'model', ''):
        patch['model'] = args.model
    if getattr(args, 'system_prompt', ''):
        patch['system_prompt'] = args.system_prompt
    if getattr(args, 'mode', ''):
        patch['mode'] = args.mode
    deny = list(getattr(args, 'tools_deny', []) or [])
    if deny:
        patch['tools.deny'] = deny
    perms: dict = {}
    for pair in (getattr(args, 'tool_permission', []) or []):
        if '=' not in pair:
            print(f'Invalid --tool-permission "{pair}" (want category=action)',
                  file=sys.stderr)
            return 1
        category, _, action = pair.partition('=')
        perms[category.strip()] = action.strip()
    persona_name = getattr(args, 'persona', '') or ''
    if persona_name:
        registry = PersonaRegistry(local_path=agent_dir / '.replio' / 'personas.json')
        persona = registry.find(persona_name)
        if persona is None:
            print(f'Unknown persona: {persona_name}', file=sys.stderr)
            return 1
        if persona.system_prompt and 'system_prompt' not in patch:
            patch['system_prompt'] = persona.system_prompt
        if persona.model and 'model' not in patch:
            patch['model'] = persona.model
        for key, value in persona.tool_permission.items():
            perms.setdefault(key, value)
    if perms:
        patch['tool_permission'] = perms
    if not patch:
        print('Nothing to set - give at least one of --provider/--model/'
              '--persona/--system-prompt/--mode/--tools-deny/--tool-permission',
              file=sys.stderr)
        return 1
    target = agent_dir / '.replio' / 'config.json'
    existing: dict = {}
    if target.exists():
        try:
            existing = json.loads(target.read_text())
        except (OSError, ValueError):
            existing = {}
    existing.update(patch)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(existing, indent=2))
    print(f'Updated {target}')
    for key, value in patch.items():
        shown = value
        if key == 'system_prompt' and len(str(value)) > 60:
            shown = str(value)[:60] + '...'
        print(f'  {key} = {shown}')
    return 0
