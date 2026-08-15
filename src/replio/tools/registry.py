class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, dict] = {}
        self._schema: list[dict] = []

    def register(self, name: str, description: str, parameters: dict,
                 refine: bool = False, category: str = 'tool',
                 permission: str = 'web', path_arg: str | None = None,
                 key_arg: str | None = None, short: str = ''):
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

    def execute(self, name: str, arguments: dict) -> str:
        tool = self._tools.get(name)
        if not tool:
            return f'Error: unknown tool "{name}"'
        props = tool['schema']['function']['parameters'].get('properties', {})
        args = {k: v for k, v in arguments.items()
                if k in props and v is not None}
        try:
            return tool['fn'](**args)
        except Exception as e:
            return f'Error executing {name}: {e}'

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
