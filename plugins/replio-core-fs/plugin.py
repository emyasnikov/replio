import fnmatch
import os
import re
from pathlib import Path

MAX_RESULT_CHARS = 8000
SKIP_DIRS = frozenset({'__pycache__', '.git', '.venv', '.replio',
                       '.opencode', 'dist', 'node_modules'})


def _truncate(text: str) -> str:
    if len(text) > MAX_RESULT_CHARS:
        return text[:MAX_RESULT_CHARS].rsplit('\n', 1)[0] + '\n... (truncated)'
    return text


def _walk(p, entries, indent, depth_left, lines):
    pad = '  ' * indent
    for e in entries:
        if e.is_dir():
            lines.append(f'{pad}{e.name}/')
            if depth_left > 1 and e.name not in SKIP_DIRS:
                try:
                    sub = sorted(e.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
                except OSError:
                    sub = []
                _walk(e, sub, indent + 1, depth_left - 1, lines)
        else:
            try:
                size = e.stat().st_size
            except OSError:
                size = 0
            lines.append(f'{pad}{e.name}  {size}')


def register_tools(registry):
    @registry.register(
        name='read_file',
        description='Read the contents of a text file. Use to inspect source code, configs, logs, or any file on disk after locating it with glob. Returns numbered lines.',
        parameters={
            'type': 'object',
            'properties': {
                'path': {
                    'type': 'string',
                    'description': 'Path to the file to read (relative to the project or absolute)',
                },
                'offset': {
                    'type': 'integer',
                    'description': '1-based line number to start reading from',
                },
                'limit': {
                    'type': 'integer',
                    'description': 'Maximum number of lines to return',
                },
            },
            'required': ['path'],
        },
        category='read',
        permission='read',
        path_arg='path',
        key_arg='path',
        short='Read the contents of a text file',
    )
    def read_file(path: str, offset: int = 1, limit: int = 500) -> str:
        p = Path(path).expanduser()
        if not p.exists():
            return f'Error: file not found: {path}'
        if p.is_dir():
            return f'Error: {path} is a directory (use list_dir instead)'
        try:
            content = p.read_text(encoding='utf-8', errors='replace')
        except OSError as e:
            return f'Error reading {path}: {e}'
        lines = content.splitlines()
        start = max(0, int(offset) - 1)
        end = len(lines) if not limit else min(len(lines), start + int(limit))
        width = len(str(end))
        out = [f'{i:>{width}}|{line}'
               for i, line in enumerate(lines[start:end], start=start + 1)]
        header = f'# {path} — {len(lines)} lines'
        if end < len(lines):
            header += f' (showing {start + 1}-{end})'
        if not out:
            return f'{header}\n(empty file)'
        return _truncate(header + '\n' + '\n'.join(out))

    @registry.register(
        name='list_dir',
        description='List a directory\'s contents. Returns sorted entries with a trailing / for subdirectories and file sizes. depth=1 lists only the immediate contents; higher values recurse into subdirectories as an indented tree. Use glob for finding files by pattern.',
        parameters={
            'type': 'object',
            'properties': {
                'path': {
                    'type': 'string',
                    'description': 'Directory to list (relative to the project or absolute)',
                },
                'depth': {
                    'type': 'integer',
                    'description': 'How many levels deep to recurse; 1 = immediate contents only',
                },
            },
            'required': ['path'],
        },
        category='read',
        permission='list',
        path_arg='path',
        key_arg='path',
        short="List a directory's contents",
    )
    def list_dir(path: str = '.', depth: int = 1) -> str:
        p = Path(path).expanduser()
        if not p.exists():
            return f'Error: path not found: {path}'
        if not p.is_dir():
            return f'Error: {path} is not a directory (use read_file instead)'
        level = max(1, int(depth))
        try:
            entries = sorted(p.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
        except OSError as e:
            return f'Error listing {path}: {e}'
        if not entries:
            return '(empty directory)'
        lines = [f'{p}:']
        _walk(p, entries, 1, level, lines)
        return _truncate('\n'.join(lines))

    @registry.register(
        name='write_file',
        description='Write content to a file, creating parent directories as needed. Use to create or update files such as source code, configs, and notes.',
        parameters={
            'type': 'object',
            'properties': {
                'path': {
                    'type': 'string',
                    'description': 'Path of the file to write (relative to the project or absolute)',
                },
                'content': {
                    'type': 'string',
                    'description': 'Full contents to write to the file',
                },
                'mode': {
                    'type': 'string',
                    'enum': ['w', 'a'],
                    'description': 'Write mode: w to overwrite, a to append',
                },
            },
            'required': ['path', 'content'],
        },
        category='write',
        permission='edit',
        path_arg='path',
        key_arg='path',
        short='Write content to a file',
    )
    def write_file(path: str, content: str, mode: str = 'w') -> str:
        p = Path(path).expanduser()
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            if mode == 'a':
                with open(p, 'a', encoding='utf-8') as f:
                    f.write(content)
                return f'Appended {len(content)} chars to {path}'
            p.write_text(content, encoding='utf-8')
        except (OSError, ValueError) as e:
            return f'Error writing {path}: {e}'
        return f'Wrote {len(content)} chars to {path}'

    @registry.register(
        name='glob',
        description='Find files and directories matching a glob pattern (e.g. "**/*.py", "src/**/chat.py"). Use to locate a file path before reading or listing it — do not guess paths.',
        parameters={
            'type': 'object',
            'properties': {
                'pattern': {
                    'type': 'string',
                    'description': 'Glob pattern; ** matches across directories',
                },
                'path': {
                    'type': 'string',
                    'description': 'Directory to search from (defaults to the current directory)',
                },
            },
            'required': ['pattern'],
        },
        category='read',
        permission='list',
        path_arg='path',
        key_arg='pattern',
        short='Find files matching a glob pattern',
    )
    def glob(pattern: str, path: str = '.') -> str:
        base = Path(path).expanduser()
        if not base.exists() or not base.is_dir():
            return f'Error: not a directory: {path}'
        matches = []
        for m in sorted(base.glob(pattern)):
            if any(p in SKIP_DIRS for p in m.relative_to(base).parts):
                continue
            try:
                rel = m.relative_to(base)
            except ValueError:
                rel = m
            matches.append(f'{rel}{"/" if m.is_dir() else ""}')
        if not matches:
            return f'(no matches for "{pattern}")'
        result = '\n'.join(matches[:200])
        if len(matches) > 200:
            result += f'\n... (showing 200 of {len(matches)} matches)'
        return _truncate(result)

    @registry.register(
        name='grep',
        description='Search file contents for a regex pattern. Returns matching file:line: text. Use to find where something is defined or used.',
        parameters={
            'type': 'object',
            'properties': {
                'pattern': {
                    'type': 'string',
                    'description': 'Regular expression to search for',
                },
                'path': {
                    'type': 'string',
                    'description': 'Directory or file to search (defaults to the current directory)',
                },
                'glob': {
                    'type': 'string',
                    'description': 'Glob to limit which files are searched (e.g. "*.py")',
                },
            },
            'required': ['pattern'],
        },
        category='read',
        permission='list',
        path_arg='path',
        key_arg='pattern',
        short='Search file contents for a pattern',
    )
    def grep(pattern: str, path: str = '.', glob: str = '*') -> str:
        try:
            regex = re.compile(pattern)
        except re.error as e:
            return f'Error: invalid regex: {e}'
        base = Path(path).expanduser()
        if not base.exists():
            return f'Error: path not found: {path}'
        files = [base] if base.is_file() else []
        if not files:
            for root, dirs, names in os.walk(base):
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
                for name in sorted(names):
                    if fnmatch.fnmatch(name, glob):
                        files.append(Path(root) / name)
        results = []
        for f in files:
            try:
                text = f.read_text(encoding='utf-8', errors='replace')
            except OSError:
                continue
            if base.is_file():
                rel = base.name
            else:
                try:
                    rel = f.relative_to(base)
                except ValueError:
                    rel = f
            for i, line in enumerate(text.splitlines(), 1):
                if regex.search(line):
                    results.append(f'{rel}:{i}: {line[:120].strip()}')
                    if len(results) >= 100:
                        break
            if len(results) >= 100:
                break
        if not results:
            return f'(no matches for "{pattern}")'
        result = '\n'.join(results[:100])
        if len(results) >= 100:
            result += '\n... (showing first 100 matches)'
        return _truncate(result)
