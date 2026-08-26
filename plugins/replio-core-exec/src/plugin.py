import subprocess
from pathlib import Path

MAX_TIMEOUT = 600
DEFAULT_TIMEOUT = 30


def _clamp_timeout(timeout) -> int:
    try:
        return max(1, min(int(timeout), MAX_TIMEOUT))
    except (TypeError, ValueError):
        return DEFAULT_TIMEOUT


def _cap(config=None) -> int:
    if config is None:
        return 0
    try:
        return max(0, int(config.get('tool_max_result_chars', 0)))
    except (TypeError, ValueError):
        return 0


def _truncate(text: str, max_chars: int = 0) -> str:
    if max_chars > 0 and len(text) > max_chars:
        return text[:max_chars].rsplit('\n', 1)[0] + '\n... (truncated)'
    return text


def register_tools(registry):
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
                    'description': 'Timeout in seconds before the command is killed (capped at 600)',
                },
            },
            'required': ['command'],
        },
        category='exec',
        permission='bash',
        key_arg='command',
        short='Run a shell command',
        echo=True,
        aliases=['bash', 'exec'],
        param_aliases={'cmd': 'command'},
    )
    def run_command(command: str, cwd: str | None = None,
                    timeout: int = 30, _config=None) -> str:
        max_chars = _cap(_config)
        if cwd and not Path(cwd).is_dir():
            return f'Error: cwd not found: {cwd}'
        timeout = _clamp_timeout(timeout)
        try:
            proc = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                cwd=cwd, timeout=timeout,
            )
        except subprocess.TimeoutExpired as e:
            out = e.stdout or ''
            return f'Error: command timed out after {timeout}s' + (f'\n{_truncate(out, max_chars)}' if out else '')
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
            lines.append(_truncate(body, max_chars))
        return '\n'.join(lines)
