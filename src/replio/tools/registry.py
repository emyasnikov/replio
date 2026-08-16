from typing import Callable


ACTIVITY_DEFAULTS: dict[str, tuple[str, str]] = {
    'read': ('←', 'Read'),
    'write': ('→', 'Write'),
    'search': ('%', 'Search'),
    'exec': ('$', 'Run'),
    'ask': ('~', 'Ask'),
    'todo': ('-', 'Todo'),
    'delegate': ('↳', 'Call'),
}


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, dict] = {}
        self._schema: list[dict] = []

    def register(self, name: str, description: str, parameters: dict,
                 refine: bool = False, category: str = 'tool',
                 permission: str = 'web', path_arg: str | None = None,
                 key_arg: str | None = None, short: str = '',
                 status: Callable[[dict], str] | None = None,
                 echo: bool = False, glyph: str = '', verb: str = ''):
        def wrapper(fn):
            entry = {
                'name': name,
                'fn': fn,
                'refine': refine,
                'category': category,
                'permission': permission,
                'path_arg': path_arg,
                'key_arg': key_arg,
                'short': short,
                'status': status,
                'echo': echo,
                'glyph': glyph,
                'verb': verb,
                'schema': {
                    'type': 'function',
                    'function': {
                        'name': name,
                        'description': description,
                        'parameters': parameters,
                    },
                },
            }
            self._tools[name] = entry
            self._schema.append(entry['schema'])
            return fn
        return wrapper

    def _clean_args(self, name: str, arguments: dict) -> dict:
        tool = self._tools.get(name)
        if not tool:
            return {}
        props = tool['schema']['function']['parameters'].get('properties', {})
        return {k: v for k, v in arguments.items()
                if k in props and v is not None}

    def execute(self, name: str, arguments: dict) -> str:
        tool = self._tools.get(name)
        if not tool:
            return f'Error: unknown tool "{name}"'
        args = self._clean_args(name, arguments)
        try:
            return tool['fn'](**args)
        except Exception as e:
            return f'Error executing {name}: {e}'

    def status_parts(self, name: str, arguments: dict) -> tuple[str, list[str]]:
        tool = self._tools.get(name)
        args = self._clean_args(name, arguments)
        if not tool:
            return name, []
        status_fn = tool.get('status')
        if status_fn:
            try:
                block = status_fn(args) or ''
                lines = block.split('\n')
                return lines[0], lines[1:]
            except Exception:
                pass
        key_arg = tool.get('key_arg')
        if key_arg and args.get(key_arg):
            return str(args[key_arg])[:80], []
        return name, []

    def echo_for(self, name: str) -> bool:
        tool = self._tools.get(name)
        return bool(tool and tool.get('echo'))

    def refine_required(self, name: str) -> bool:
        tool = self._tools.get(name)
        return bool(tool and tool.get('refine'))

    def permission_for(self, name: str) -> str:
        tool = self._tools.get(name)
        return tool['permission'] if tool else 'web'

    def path_arg_for(self, name: str) -> str | None:
        tool = self._tools.get(name)
        return tool['path_arg'] if tool else None

    def key_arg_for(self, name: str) -> str | None:
        tool = self._tools.get(name)
        return tool['key_arg'] if tool else None

    def activity(self, name: str, arguments: dict) -> tuple[str, str, str] | None:
        tool = self._tools.get(name)
        if not tool:
            return None
        args = self._clean_args(name, arguments)
        glyph = tool.get('glyph')
        verb = tool.get('verb')
        if not glyph or not verb:
            defaults = ACTIVITY_DEFAULTS.get(tool['category'])
            if defaults is None:
                return None
            d_glyph, d_verb = defaults
            glyph = glyph or d_glyph
            verb = verb or d_verb
        key_arg = tool.get('key_arg')
        label = str(args[key_arg])[:80] if key_arg and args.get(key_arg) else name
        return glyph, verb, label

    def info(self, name: str) -> dict | None:
        tool = self._tools.get(name)
        if not tool:
            return None
        return {
            'name': name,
            'description': tool['schema']['function']['description'],
            'short': tool['short'] or tool['schema']['function']['description'][:60],
            'category': tool['category'],
            'permission': tool['permission'],
            'parameters': tool['schema']['function']['parameters'],
        }

    def schema(self) -> list[dict]:
        return list(self._schema)

    def schema_filtered(self, allowed: set[str]) -> list[dict]:
        return [s for s in self._schema if s['function']['name'] in allowed]

    def names(self) -> list[str]:
        return list(self._tools.keys())
