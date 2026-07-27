import sys
import argparse

from .config import Config
from .chat import ChatLoop


def main():
    parser = argparse.ArgumentParser(
        description='REPL.ai — A terminal-based REPL AI chat application'
    )
    parser.add_argument(
        '--path', '-p',
        help='Project path (default: current directory)'
    )
    args = parser.parse_args()

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
