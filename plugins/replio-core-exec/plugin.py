import subprocess

MAX_RESULT_CHARS = 8000


def _truncate(text: str) -> str:
    if len(text) > MAX_RESULT_CHARS:
        return text[:MAX_RESULT_CHARS].rsplit('\n', 1)[0] + '\n... (truncated)'
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
                    'description': 'Timeout in seconds before the command is killed',
                },
            },
            'required': ['command'],
        },
        category='exec',
        permission='bash',
        key_arg='command',
        short='Run a shell command',
        echo=True,
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
