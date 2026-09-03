import sys
import argparse

from .config import Config
from .chat import ChatLoop
from . import get_version


def _add_run_parser(sub):
    p = sub.add_parser('run', help='One-shot headless chat (JSON or text output)')
    p.add_argument('--prompt', '-p', required=True, help='The prompt to send')
    p.add_argument('--provider', help='Provider override (e.g. ollama, openai, groq)')
    p.add_argument('--model', help='Model override')
    p.add_argument('--base-url', help='Base URL override')
    p.add_argument('--mode', help='Agent mode override (plan, build, or a custom mode)')
    p.add_argument('--output', choices=['text', 'json'], default='json',
                   help='Output format (default: json)')
    p.add_argument('--verbose', action='store_true',
                   help='Print tool status and diagnostics to stderr')
    p.add_argument('--session-id', help='Persistent session name (load or create)')
    g = p.add_mutually_exclusive_group()
    g.add_argument('--yes', dest='approve', action='store_true',
                   help='Auto-approve tools that require confirmation')
    g.add_argument('--no', dest='approve', action='store_false',
                   help='Auto-deny tools that require confirmation (default)')
    p.set_defaults(approve=None)
    p.add_argument('--path', default=argparse.SUPPRESS,
                   help='Project path (default: current directory)')


def _add_export_parser(sub):
    p = sub.add_parser('export', help='Export a saved session to Markdown')
    p.add_argument('name', help='Session name to export')
    p.add_argument('--out', help='Output file (default: .replio/exports/<name>.md, - for stdout)')
    p.add_argument('--path', default=argparse.SUPPRESS,
                   help='Project path (default: current directory)')


def _add_models_parser(sub):
    p = sub.add_parser('models', help='List models available from the connected provider')
    p.add_argument('--path', default=argparse.SUPPRESS,
                   help='Project path (default: current directory)')


def _add_eval_parser(sub):
    p = sub.add_parser('eval', help='Tool-use evaluation harness '
                       '(run task fixtures headless and report metrics)')
    p.add_argument('--path', default=argparse.SUPPRESS,
                   help='Project path (default: current directory)')
    g = p.add_subparsers(dest='action', required=True)
    g.add_parser('list', help='List discovered eval fixtures')
    r = g.add_parser('run', help='Run the fixture suite and report metrics')
    r.add_argument('--fixture', help='Fixture id or substring to run (default: all)')
    r.add_argument('--provider', help='Provider override')
    r.add_argument('--model', help='Model override')
    r.add_argument('--base-url', help='Base URL override')
    r.add_argument('--compare', help='Comma-separated providers to compare, '
                   'e.g. ollama,openai')
    r.add_argument('--output', choices=['table', 'json'], default='table',
                   help='Output format (default: table)')
    r.add_argument('--verbose', action='store_true',
                   help='Print tool status and diagnostics to stderr')


def _add_serve_parser(sub):
    p = sub.add_parser('serve', help='HTTP JSON API server (stdlib http.server)')
    p.add_argument('--host', default='127.0.0.1')
    p.add_argument('--port', type=int, default=8787)
    p.add_argument('--path', default=argparse.SUPPRESS,
                   help='Project path (default: current directory)')
    p.add_argument('--mode', help='Agent mode override (plan, build, or a custom mode)')


def _add_mcp_parser(sub):
    p = sub.add_parser('mcp', help='Run replio as an MCP server over stdio')
    p.add_argument('--path', default=argparse.SUPPRESS,
                   help='Project path (default: current directory)')


def _add_config_parser(sub):
    p = sub.add_parser('config',
                       help='Show, set, or unset config values (global or project-local scope)')
    p.add_argument('--path', default=argparse.SUPPRESS,
                   help='Project path (default: current directory)')
    g = p.add_subparsers(dest='action', required=True)
    gg = g.add_parser('get', help='Show effective values (one or more keys, default: all)')
    gg.add_argument('key', nargs='*')
    gg.add_argument('--show-origin', action='store_true',
                    help='Also print where each value comes from (default/global/local)')
    gs = g.add_parser('set', help='Set a config value')
    gs.add_argument('key')
    gs.add_argument('value', nargs='?')
    gu = g.add_parser('unset', help='Remove a config value from the selected scope')
    gu.add_argument('key')
    for sub in (gg, gs, gu):
        sub.add_argument('--global', dest='global_', action='store_true',
                         help='Use the global config file (~/.config/replio/config.json)')
        sub.add_argument('--local', dest='local_', action='store_true',
                         help='Use the project-local config file (default)')


def _add_plugins_parser(sub):
    p = sub.add_parser('plugins', help='Manage plugins (list, install, update, uninstall)')
    p.add_argument('--path', default=argparse.SUPPRESS,
                   help='Project path (default: current directory)')
    g = p.add_subparsers(dest='action', required=True)
    g.add_parser('list', help='List installed plugins')
    pi = g.add_parser('install', help='Install a plugin from a git URL or local path')
    pi.add_argument('source', help='Git URL or local path of the plugin')
    pi.add_argument('--global', dest='global_', action='store_true',
                    help='Install into the global plugins dir')
    pi.add_argument('--deps', action='store_true',
                    help='pip install the plugin\'s declared dependencies')
    pu = g.add_parser('update', help='Update an installed plugin')
    pu.add_argument('name', help='Plugin name')
    pun = g.add_parser('uninstall', help='Remove an installed plugin')
    pun.add_argument('name', help='Plugin name')
    pt = g.add_parser('test', help='Run a plugin\'s bundled test suite')
    pt.add_argument('name', nargs='?', help='Plugin name (default: all plugins with tests)')
    pt.add_argument('--verbose', action='store_true', help='Verbose unittest output')


def _add_jobs_parser(sub):
    p = sub.add_parser('jobs',
                       help='Scheduled and durable jobs (cron-style, retries, approvals)')
    p.add_argument('--path', default=argparse.SUPPRESS,
                   help='Project path (default: current directory)')
    g = p.add_subparsers(dest='action', required=True)
    g.add_parser('list', help='List configured jobs')
    g.add_parser('status', help='Runtime summary per job (fired count, last error, uptime)')
    gs = g.add_parser('show', help='Show a job definition and its run history')
    gs.add_argument('name')
    ga = g.add_parser('add', help='Add a job (starts as proposed, needs approval)')
    ga.add_argument('name')
    ga.add_argument('--prompt', default='',
                    help='Optional short per-run prompt (required unless --file is given)')
    ga.add_argument('--file', help='Markdown task file describing the job '
                    '(default .replio/jobs/<name>.md, created as a template if missing). '
                    'Linked - edits apply on the next run')
    sched = ga.add_mutually_exclusive_group(required=True)
    sched.add_argument('--cron', help='5-field cron expression (minute hour dom month dow)')
    sched.add_argument('--interval', type=int, help='Seconds between runs (min 60)')
    sched.add_argument('--at', help='One-shot run at an ISO datetime (e.g. 2026-08-27T02:00:00Z)')
    ga.add_argument('--session', help='Stable session name (default: a fresh '
                    'job_<ts>_<name> file per run)')
    ga.add_argument('--mode', help='Agent mode override (plan, build, or custom)')
    ga.add_argument('--provider', help='Provider override')
    ga.add_argument('--model', help='Model override')
    ga.add_argument('--type', help='Agent type whose prompt, model, and permissions apply')
    ga.add_argument('--system-prompt', help='System prompt override')
    ga.add_argument('--tools-deny', action='append', default=[],
                    help='Tool name to deny (repeatable)')
    ga.add_argument('--tool-permission', action='append', default=[],
                    help='category=action override (repeatable), e.g. bash=allow')
    ga.add_argument('--retries', type=int, default=3, help='Retries after a failed run')
    ga.add_argument('--backoff', type=float, default=60.0,
                    help='Base backoff seconds, doubled per retry')
    ga.add_argument('--timeout', type=int, default=0,
                    help='Max seconds for a run (0 = no cap)')
    ga.add_argument('--require-approval', action='store_true',
                    help='Arm only one run per approve - each run parks in waiting_approval '
                         'until a human approves it')
    ga.add_argument('--approval', choices=['manual', 'auto'], default='manual',
                    help='manual starts proposed and waits for approve (default); '
                         'auto starts approved')
    for name, help_text in (
            ('approve', 'Approve a job so it runs on schedule'),
            ('reject', 'Reject a proposed job'),
            ('enable', 'Enable a disabled job'),
            ('disable', 'Disable a job'),
            ('stop', 'Stop a job - same as disable, no scheduled runs'),
            ('edit', 'Open the job task file in $EDITOR (creates the template first)'),
            ('remove', 'Remove a job definition')):
        cmd = g.add_parser(name, help=help_text)
        cmd.add_argument('name')
    gr = g.add_parser('run', help='Run a job now (waits, applies retries)')
    gr.add_argument('name')
    gr.add_argument('--no-retry', action='store_true',
                    help='Single attempt, no retries or backoff')
    gr.add_argument('--verbose', action='store_true',
                    help='Stream the run live (tokens, tool activity) before the summary')
    gd = g.add_parser('daemon', help='Run the scheduler loop until interrupted')
    gd.add_argument('--tick', type=float, default=15.0,
                    help='Schedule check interval in seconds (default: 15)')
    gd.add_argument('--quiet', action='store_true', help='Suppress scheduler output')


def _add_fleet_parser(sub):
    p = sub.add_parser('fleet', help='Supervise a fleet of scoped replio serve agents '
                       '(ports, health checks, restart policy, config generation)')
    p.add_argument('--path', default=argparse.SUPPRESS,
                   help='Fleet root (default: current directory)')
    g = p.add_subparsers(dest='action', required=True)
    g.add_parser('init', help='Scan subdirectories holding .replio/config.json '
                 'into the fleet manifest')
    ga = g.add_parser('add', help='Add an agent to the manifest')
    ga.add_argument('name')
    ga.add_argument('--dir', help='Agent directory (default: <root>/<name>)')
    ga.add_argument('--port', type=int, default=0,
                    help='Preferred port (0 = auto-allocate)')
    ga.add_argument('--max-restarts', type=int, default=10,
                    help='Restart budget before the supervisor pauses the agent '
                         '(0 = unlimited)')
    grm = g.add_parser('remove', help='Remove an agent from the manifest (stops it)')
    grm.add_argument('name')
    gu = g.add_parser('up', help='Start agents (Ctrl-C = graceful down)')
    gu.add_argument('--detach', action='store_true',
                    help='Run the supervisor as a background daemon')
    gu.add_argument('--daemon', dest='daemon_', action='store_true',
                    help=argparse.SUPPRESS)
    g.add_parser('down', help='Stop the supervised agents and the daemon if running')
    g.add_parser('status', help='Live status table of the fleet')
    gr = g.add_parser('restart', help='Stop and relaunch agents, resetting backoff')
    gr.add_argument('name', nargs='?', help='Agent name (default: all)')
    gl = g.add_parser('logs', help='Show an agent log (tail)')
    gl.add_argument('name')
    gl.add_argument('n', nargs='?', type=int, default=50,
                    help='Last N lines (default: 50)')
    gl.add_argument('--follow', '-f', action='store_true',
                    help='Keep watching appended output (Ctrl-C to stop)')
    gc = g.add_parser('config', help='Write selected keys into <agent>/.replio/config.json')
    gc.add_argument('name')
    gc.add_argument('--provider', help='Provider override')
    gc.add_argument('--model', help='Model override')
    gc.add_argument('--type', help='Inline an agent type\'s prompt, model, and permissions')
    gc.add_argument('--system-prompt', help='System prompt override')
    gc.add_argument('--mode', help='Agent mode override (plan, build, or custom)')
    gc.add_argument('--tools-deny', action='append', default=[],
                    help='Tool name to deny (repeatable)')
    gc.add_argument('--tool-permission', action='append', default=[],
                    help='category=action override (repeatable), e.g. bash=allow')


def _version():
    return get_version()


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Replio - a terminal-based agentic REPL with headless CLI and API modes'
    )
    parser.add_argument('--path', '-p', help='Project path (default: current directory)')
    parser.add_argument('--version', '-v', action='version',
                        help='Print version and exit', version=_version())
    sub = parser.add_subparsers(dest='command')
    _add_run_parser(sub)
    _add_export_parser(sub)
    _add_models_parser(sub)
    _add_eval_parser(sub)
    _add_serve_parser(sub)
    _add_mcp_parser(sub)
    _add_config_parser(sub)
    _add_plugins_parser(sub)
    _add_jobs_parser(sub)
    _add_fleet_parser(sub)
    args = parser.parse_args(argv)

    if args.command == 'run':
        from .cli import cmd_run
        return cmd_run(args)
    if args.command == 'export':
        from .cli import cmd_export
        return cmd_export(args)
    if args.command == 'models':
        from .cli import cmd_models
        return cmd_models(args)
    if args.command == 'eval':
        from .cli import cmd_eval
        return cmd_eval(args)
    if args.command == 'serve':
        from .cli import cmd_serve
        return cmd_serve(args)
    if args.command == 'mcp':
        from .cli import cmd_mcp
        return cmd_mcp(args)
    if args.command == 'plugins':
        from .cli import cmd_plugins
        return cmd_plugins(args)
    if args.command == 'config':
        from .cli import cmd_config
        return cmd_config(args)
    if args.command == 'jobs':
        from .cli import cmd_jobs
        return cmd_jobs(args)
    if args.command == 'fleet':
        from .cli import cmd_fleet
        return cmd_fleet(args)

    config = Config(path=args.path)
    chat = ChatLoop(config)

    try:
        chat.run()
    except SystemExit:
        pass
    except KeyboardInterrupt:
        print()
    except Exception as e:
        print(f'\nUnexpected error: {e}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
