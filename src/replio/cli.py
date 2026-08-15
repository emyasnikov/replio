import json
import sys

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
    auto = 'allow' if getattr(args, 'approve', None) is True else 'deny'
    ui = HeadlessUI(auto=auto, verbose=getattr(args, 'verbose', False),
                    stream=getattr(args, 'output', 'json') == 'text')
    return Engine(config, ui=ui)


def cmd_run(args) -> int:
    engine = _engine_from_args(args)
    engine.load_or_create_session(getattr(args, 'session_id', None))
    result = engine.chat(args.prompt, autoname=getattr(args, 'session_id', None) is None)
    if args.output == 'json':
        sys.stdout.write(json.dumps(result.to_dict(), indent=2) + '\n')
    return 0 if result.status in ('ok', 'truncated') else 1


def cmd_serve(args) -> int:
    from .server import HeadlessServer, ChatHandler
    config = Config(path=args.path)
    ui = HeadlessUI(auto='deny', verbose=False, stream=False)
    engine = Engine(config, ui=ui)
    server = HeadlessServer((args.host, args.port), ChatHandler, engine=engine)
    print(f'replio serve — http://{args.host}:{args.port} '
          f'(POST /chat, GET /sessions, GET /health, GET /version)', file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0
