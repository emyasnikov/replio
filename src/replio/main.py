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
    _add_serve_parser(sub)
    _add_mcp_parser(sub)
    _add_plugins_parser(sub)
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
    if args.command == 'serve':
        from .cli import cmd_serve
        return cmd_serve(args)
    if args.command == 'mcp':
        from .cli import cmd_mcp
        return cmd_mcp(args)

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
