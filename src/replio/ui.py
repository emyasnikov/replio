import sys


def render_markdown(token: str, state: dict) -> list[tuple[str, str]]:
    segments = []
    while token:
        if state['code_block']:
            idx = token.find('```')
            if idx != -1:
                before = token[:idx]
                if before:
                    segments.append((before, '\033[36m'))
                state['code_block'] = False
                token = token[idx + 3:]
            else:
                segments.append((token, '\033[36m'))
                token = ''
        elif state['inline_code']:
            idx = token.find('`')
            if idx != -1:
                before = token[:idx]
                if before:
                    segments.append((before, '\033[32m'))
                state['inline_code'] = False
                token = token[idx + 1:]
            else:
                segments.append((token, '\033[32m'))
                token = ''
        elif state['bold']:
            idx = token.find('**')
            if idx != -1:
                before = token[:idx]
                if before:
                    segments.append((before, '\033[1m'))
                state['bold'] = False
                token = token[idx + 2:]
            else:
                segments.append((token, '\033[1m'))
                token = ''
        else:
            idx = -1
            marker = ''
            for m in ('```', '**', '`'):
                pos = token.find(m)
                if pos != -1 and (idx == -1 or pos < idx):
                    idx = pos
                    marker = m
            if idx != -1:
                before = token[:idx]
                if before:
                    segments.append((before, ''))
                if marker == '```':
                    state['code_block'] = True
                elif marker == '**':
                    state['bold'] = True
                elif marker == '`':
                    state['inline_code'] = True
                token = token[idx + len(marker):]
            else:
                segments.append((token, ''))
                token = ''
    return segments


class ReplUI:
    def __init__(self, loop):
        self._loop = loop
        self.first_content = True
        self.content_newline = True
        self.md_state = {'code_block': False, 'inline_code': False, 'bold': False}

    def _prefix(self):
        if self.first_content:
            sys.stdout.write('\001\033[33m\002<<< \001\033[0m\002')
            sys.stdout.flush()
            self.first_content = False

    def _write(self, text, ansi=''):
        if ansi:
            sys.stdout.write(f'\001{ansi}\002{text}\001\033[0m\002')
        else:
            sys.stdout.write(text)
        sys.stdout.flush()

    def _emit(self, text, ansi='', newline=True):
        self._write(text, ansi)
        if newline:
            sys.stdout.write('\n')
            sys.stdout.flush()

    def token(self, text):
        self._prefix()
        if self._loop.config.get('markdown_streaming'):
            for seg, ansi in render_markdown(text, self.md_state):
                self._write(seg, ansi)
        else:
            self._write(text)
        self.content_newline = text.endswith('\n')

    def thinking_begin(self):
        if not self._loop.config.get('show_thinking', True):
            return
        self._emit('- Thinking', '\033[90m')
        self.content_newline = True

    def thinking(self, text):
        if not self._loop.config.get('show_thinking', True):
            return
        self._write(text, '\033[90m')
        self.content_newline = text.endswith('\n')

    def thinking_end(self, duration):
        if self._loop.config.get('show_thinking', True):
            sys.stdout.write('\n')
            sys.stdout.flush()
        else:
            self._emit(f'+ Thought {duration:.1f}s', '\033[90m')
        self.content_newline = True

    def warning(self, msg):
        self._emit(f'[warning] {msg}', '\033[93m')

    def error(self, code, msg):
        label = f'[Error {code}]' if code else '[Error]'
        self._emit(f'{label} {msg}', '\033[91m')

    def tool_status(self, name, value, body):
        self._emit(f'[{name}: {value}]', '\033[90m')
        for line in body:
            self._emit(line, '\033[90m')

    def tool_result(self, output):
        for line in output.splitlines():
            self._emit(line, '\033[90m')

    def tool_refine(self, old, new):
        self._emit(f'[refine: "{old}" → "{new}"]', '\033[90m')

    def footer(self, duration, usage, tokens):
        if not self.content_newline:
            sys.stdout.write('\n')
            sys.stdout.flush()
        if self._loop.config.get('show_context_size', True):
            self._emit(f'({duration:.1f}s, {tokens:,} tokens)', '\033[90m')
        else:
            self._emit(f'({duration:.1f}s)', '\033[90m')
        self.content_newline = True

    def info(self, msg):
        self._emit(msg)

    def confirm(self, name, label):
        try:
            answer = input(
                f'\001\033[90m\002  ↳ {label} — approve? [y/N] \001\033[0m\002'
            ).strip().lower()
        except (EOFError, KeyboardInterrupt):
            sys.stdout.write('\n')
            return False
        return answer in ('y', 'yes')


class NullUI:
    def token(self, text):
        pass

    def thinking(self, text):
        pass

    def thinking_begin(self):
        pass

    def thinking_end(self, duration):
        pass

    def warning(self, msg):
        pass

    def error(self, code, msg):
        pass

    def tool_status(self, name, value, body):
        pass

    def tool_result(self, output):
        pass

    def tool_refine(self, old, new):
        pass

    def footer(self, duration, usage, tokens):
        pass

    def info(self, msg):
        pass

    def confirm(self, name, label):
        return False


class HeadlessUI:
    def __init__(self, auto: str = 'deny', verbose: bool = False, stream: bool = True,
                 show_thinking: bool = True):
        self.auto = auto
        self.verbose = verbose
        self.stream = stream
        self.show_thinking = show_thinking

    def token(self, text):
        if self.stream:
            sys.stdout.write(text)
            sys.stdout.flush()

    def thinking(self, text):
        if self.verbose and self.stream:
            sys.stderr.write(text)
            sys.stderr.flush()

    def thinking_begin(self):
        if self.verbose and self.stream and self.show_thinking:
            sys.stderr.write('- Thinking\n')

    def thinking_end(self, duration):
        if not (self.verbose and self.stream):
            return
        if self.show_thinking:
            sys.stderr.write('\n')
        else:
            sys.stderr.write(f'+ Thought {duration:.1f}s\n')

    def warning(self, msg):
        sys.stderr.write(f'[warning] {msg}\n')

    def error(self, code, msg):
        label = f'[Error {code}]' if code else '[Error]'
        sys.stderr.write(f'{label} {msg}\n')

    def tool_status(self, name, value, body):
        if self.verbose:
            sys.stderr.write(f'[{name}: {value}]\n')
            for line in body:
                sys.stderr.write(f'{line}\n')

    def tool_result(self, output):
        if self.verbose:
            sys.stderr.write(output.rstrip('\n') + '\n')

    def tool_refine(self, old, new):
        if self.verbose:
            sys.stderr.write(f'[refine: "{old}" → "{new}"]\n')

    def footer(self, duration, usage, tokens):
        if self.stream:
            sys.stderr.write(f'({duration:.1f}s, {tokens:,} tokens)\n')

    def info(self, msg):
        if self.verbose:
            sys.stderr.write(msg + '\n')

    def confirm(self, name, label):
        return self.auto == 'allow'
