import sys
import argparse
from importlib.metadata import version, PackageNotFoundError

from .config import Config
from .chat import ChatLoop


def _add_run_parser(sub):
    p = sub.add_parser('run', help='One-shot headless chat (JSON or text output)')
    p.add_argument('--prompt', '-p', required=True, help='The prompt to send')
    p.add_argument('--provider', help='Provider override (e.g. ollama, openai, groq)')
    p.add_argument('--model', help='Model override')
    p.add_argument('--base-url', help='Base URL override')
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
    p.add_argument('--path', help='Project path (default: current directory)')


def _add_serve_parser(sub):
    p = sub.add_parser('serve', help='HTTP JSON API server (stdlib http.server)')
    p.add_argument('--host', default='127.0.0.1')
    p.add_argument('--port', type=int, default=8787)
    p.add_argument('--path', help='Project path (default: current directory)')


def _version():
    try:
        return version('replio')
    except PackageNotFoundError:
        return 'unknown'


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='REPL.io — a terminal-based agentic REPL with headless CLI and API modes'
    )
    parser.add_argument('--path', '-p', help='Project path (default: current directory)')
    parser.add_argument('--version', '-v', action='version',
                        help='Print version and exit', version=_version())
    sub = parser.add_subparsers(dest='command')
    _add_run_parser(sub)
    _add_serve_parser(sub)
    args = parser.parse_args(argv)

    if args.command == 'run':
        from .cli import cmd_run
        return cmd_run(args)
    if args.command == 'serve':
        from .cli import cmd_serve
        return cmd_serve(args)

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
