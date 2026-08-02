class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, dict] = {}
        self._schema: list[dict] = []

    def register(self, name: str, description: str, parameters: dict,
                 refine: bool = False):
        def wrapper(fn):
            entry = {
                'name': name,
                'fn': fn,
                'refine': refine,
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
        try:
            return tool['fn'](**arguments)
        except Exception as e:
            return f'Error executing {name}: {e}'

    def refine_required(self, name: str) -> bool:
        tool = self._tools.get(name)
        return bool(tool and tool.get('refine'))

    def schema(self) -> list[dict]:
        return list(self._schema)

    def names(self) -> list[str]:
        return list(self._tools.keys())
