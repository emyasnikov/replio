import sys
import threading
import time


SPINNER_FRAMES = ('⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏')
SPINNER_INTERVAL = 0.08


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
        self._spinner_thread: threading.Thread | None = None
        self._spinner_stop = threading.Event()
        self._spinner_lock = threading.Lock()
        self._spinner_frame = 0
        self._word_buffer = ''

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
        if self._loop.config.get('word_streaming', True):
            self._word_buffer += text
            self._flush_words()
        else:
            self._render(text)

    def _render(self, text):
        self._prefix()
        if self._loop.config.get('markdown_streaming'):
            for seg, ansi in render_markdown(text, self.md_state):
                self._write(seg, ansi)
        else:
            self._write(text)
        self.content_newline = text.endswith('\n')

    def _flush_words(self):
        last = -1
        for i, ch in enumerate(self._word_buffer):
            if ch.isspace():
                last = i
        if last == -1:
            return
        self._render(self._word_buffer[:last + 1])
        self._word_buffer = self._word_buffer[last + 1:]

    def flush(self):
        if self._word_buffer:
            self._render(self._word_buffer)
            self._word_buffer = ''

    def thinking_begin(self):
        self.flush()
        if not self._loop.config.get('show_thinking', True):
            self._start_spinner()
            return
        self._emit('- Thinking', '\033[90m')
        self.content_newline = True

    def _spinner_run(self):
        while not self._spinner_stop.is_set():
            frame = SPINNER_FRAMES[self._spinner_frame % len(SPINNER_FRAMES)]
            self._spinner_frame += 1
            with self._spinner_lock:
                if self._spinner_stop.is_set():
                    break
                sys.stdout.write(f'\r\033[K{frame} Thinking')
                sys.stdout.flush()
            time.sleep(SPINNER_INTERVAL)

    def _start_spinner(self):
        if self._spinner_thread is not None and self._spinner_thread.is_alive():
            return
        self._spinner_stop.clear()
        self._spinner_frame = 0
        self._spinner_thread = threading.Thread(
            target=self._spinner_run, name='replio-spinner', daemon=True)
        self._spinner_thread.start()

    def _stop_spinner(self):
        if self._spinner_thread is None or not self._spinner_thread.is_alive():
            self._spinner_thread = None
            return
        self._spinner_stop.set()
        self._spinner_thread.join(timeout=0.5)
        self._spinner_thread = None
        with self._spinner_lock:
            sys.stdout.write('\r\033[K')
            sys.stdout.flush()

    def thinking(self, text):
        self.flush()
        if not self._loop.config.get('show_thinking', True):
            return
        self._write(text, '\033[90m')
        self.content_newline = text.endswith('\n')

    def thinking_end(self, duration):
        self.flush()
        self._stop_spinner()
        if self._loop.config.get('show_thinking', True):
            sys.stdout.write('\n')
            sys.stdout.flush()
            if self._loop.config.get('show_thought_duration', True):
                self._emit(f'(Thought {duration:.1f}s)', '\033[90m')
        else:
            self._emit(f'+ Thought {duration:.1f}s', '\033[90m')
        self.content_newline = True

    def warning(self, msg):
        self.flush()
        self._emit(f'[warning] {msg}', '\033[93m')

    def error(self, code, msg):
        self.flush()
        label = f'[Error {code}]' if code else '[Error]'
        self._emit(f'{label} {msg}', '\033[91m')

    def tool_status(self, name, value, body):
        self.flush()
        self._emit(f'[{name}: {value}]', '\033[90m')
        for line in body:
            self._emit(line, '\033[90m')

    def activity(self, glyph, verb, label, body):
        self.flush()
        self._emit(f'{glyph} {verb} {label}', '\033[90m')
        for line in body:
            self._emit(line, '\033[90m')

    def tool_error(self, msg):
        self.flush()
        self._emit(f'! {msg.split(chr(10), 1)[0]}', '\033[90m')

    def tool_note(self, output):
        self.flush()
        lines = [l for l in output.splitlines() if l]
        self._emit(lines[-1], '\033[90m')

    def tool_result(self, output):
        self.flush()
        for line in output.splitlines():
            self._emit(line, '\033[90m')

    def tool_refine(self, old, new):
        self.flush()
        self._emit(f'[refine: "{old}" → "{new}"]', '\033[90m')

    def _footer_tokens(self, counts):
        parts = []
        for key in self._loop.config.get('footer_tokens', ['context']):
            n = counts.get(key)
            if n is None:
                continue
            if key == 'context':
                parts.append(f'{n:,} tokens')
            else:
                parts.append(f'{n}t')
        return '/'.join(parts)

    def footer(self, duration, counts):
        self.flush()
        if not self.content_newline:
            sys.stdout.write('\n')
            sys.stdout.flush()
        if self._loop.config.get('show_context_size', True):
            seg = self._footer_tokens(counts)
            body = f'({duration:.1f}s, {seg})' if seg else f'({duration:.1f}s)'
            self._emit(body, '\033[90m')
        else:
            self._emit(f'({duration:.1f}s)', '\033[90m')
        self.content_newline = True

    def info(self, msg):
        self.flush()
        self._emit(msg)

    def confirm(self, name, label):
        self.flush()
        try:
            answer = input(
                f'\001\033[90m\002? {label} - approve? [y/N] \001\033[0m\002'
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

    def activity(self, glyph, verb, label, body):
        pass

    def tool_error(self, msg):
        pass

    def tool_note(self, output):
        pass

    def tool_result(self, output):
        pass

    def tool_refine(self, old, new):
        pass

    def footer(self, duration, counts):
        pass

    def info(self, msg):
        pass

    def confirm(self, name, label):
        return False


class HeadlessUI:
    def __init__(self, auto: str = 'deny', verbose: bool = False, stream: bool = True,
                 show_thinking: bool = True, show_thought_duration: bool = True,
                 footer_tokens: list | None = None):
        self.auto = auto
        self.verbose = verbose
        self.stream = stream
        self.show_thinking = show_thinking
        self.show_thought_duration = show_thought_duration
        self.footer_tokens = footer_tokens or ['context']

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
            if self.show_thought_duration:
                sys.stderr.write(f'(Thought {duration:.1f}s)\n')
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

    def activity(self, glyph, verb, label, body):
        if self.verbose:
            sys.stderr.write(f'{glyph} {verb} {label}\n')
            for line in body:
                sys.stderr.write(f'{line}\n')

    def tool_error(self, msg):
        if self.verbose:
            sys.stderr.write(f'! {msg.split(chr(10), 1)[0]}\n')

    def tool_note(self, output):
        if self.verbose:
            lines = [l for l in output.splitlines() if l]
            sys.stderr.write(lines[-1] + '\n')

    def tool_result(self, output):
        if self.verbose:
            sys.stderr.write(output.rstrip('\n') + '\n')

    def tool_refine(self, old, new):
        if self.verbose:
            sys.stderr.write(f'[refine: "{old}" → "{new}"]\n')

    def footer(self, duration, counts):
        if self.stream:
            parts = []
            for key in self.footer_tokens:
                n = counts.get(key)
                if n is None:
                    continue
                parts.append(f'{n:,} tokens' if key == 'context' else f'{n}t')
            seg = '/'.join(parts)
            if seg:
                sys.stderr.write(f'({duration:.1f}s, {seg})\n')
            else:
                sys.stderr.write(f'({duration:.1f}s)\n')

    def info(self, msg):
        if self.verbose:
            sys.stderr.write(msg + '\n')

    def confirm(self, name, label):
        return self.auto == 'allow'
