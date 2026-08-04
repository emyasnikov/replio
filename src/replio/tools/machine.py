import subprocess
from pathlib import Path

MAX_RESULT_CHARS = 8000


def _truncate(text: str) -> str:
    if len(text) > MAX_RESULT_CHARS:
        return text[:MAX_RESULT_CHARS].rsplit('\n', 1)[0] + '\n... (truncated)'
    return text


def register_machine_tools(registry):
    @registry.register(
        name='read_file',
        description='Read the contents of a text file. Use to inspect source code, configs, logs, or any file on disk. Returns numbered lines.',
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
        result = '\n'.join(out)
        if end < len(lines):
            result += f'\n... (showing lines {start + 1}-{end} of {len(lines)})'
        return _truncate(result) if result else '(empty file)'

    @registry.register(
        name='list_dir',
        description='List the contents of a directory. Returns sorted entries with a trailing / for subdirectories and file sizes.',
        parameters={
            'type': 'object',
            'properties': {
                'path': {
                    'type': 'string',
                    'description': 'Directory to list (relative to the project or absolute)',
                },
            },
            'required': ['path'],
        },
        category='read',
        permission='list',
        path_arg='path',
        key_arg='path',
    )
    def list_dir(path: str = '.') -> str:
        p = Path(path).expanduser()
        if not p.exists():
            return f'Error: path not found: {path}'
        if not p.is_dir():
            return f'Error: {path} is not a directory (use read_file instead)'
        try:
            entries = sorted(p.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
        except OSError as e:
            return f'Error listing {path}: {e}'
        if not entries:
            return '(empty directory)'
        lines = [f'{p}:']
        for e in entries:
            if e.is_dir():
                lines.append(f'  {e.name}/')
            else:
                try:
                    size = e.stat().st_size
                except OSError:
                    size = 0
                lines.append(f'  {e.name}  {size}')
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
        name='run_command',
        description='Run a shell command in the project environment. Captures stdout/stderr and the exit code. Use for builds, tests, git operations, and any terminal task.',
        parameters={
            'type': 'object',
            'properties': {
                'command': {
                    'type': 'string',
                    'description': 'The shell command to execute',
                },
                'cwd': {
                    'type': 'string',
                    'description': 'Working directory for the command (defaults to the current one)',
                },
                'timeout': {
                    'type': 'integer',
                    'description': 'Timeout in seconds before the command is killed',
                },
            },
            'required': ['command'],
        },
        category='exec',
        permission='bash',
        key_arg='command',
    )
    def run_command(command: str, cwd: str | None = None,
                    timeout: int = 30) -> str:
        try:
            proc = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                cwd=cwd, timeout=timeout,
            )
        except subprocess.TimeoutExpired as e:
            out = e.stdout or ''
            return f'Error: command timed out after {timeout}s' + (f'\n{_truncate(out)}' if out else '')
        except OSError as e:
            return f'Error running command: {e}'
        stdout = proc.stdout or ''
        stderr = proc.stderr or ''
        body = stdout if not stderr or stderr == stdout else f'{stdout}\n{stderr}'
        lines = [f'$ {command}']
        if cwd:
            lines.append(f'[cwd: {cwd}]')
        lines.append(f'exit {proc.returncode}')
        if body:
            lines.append(_truncate(body))
        return '\n'.join(lines)
