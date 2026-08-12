import sys
import json
import readline
import os
from datetime import datetime, timezone

from .config import Config
from .sessions.manager import SessionManager
from .commands.registry import CommandRegistry
from .commands.builtins import register_builtins

HISTFILE = '.replio_history'


class _StreamRenderer:
    def __init__(self, show_thinking: bool, markdown: bool, render_token):
        self.show_thinking = show_thinking
        self.markdown = markdown
        self.render_token = render_token
        self.first_content = True
        self.thinking = False
        self.thinking_text = ''
        self.md_state = {'code_block': False, 'inline_code': False, 'bold': False}
        self.content = ''

    def _prefix(self):
        if self.first_content:
            sys.stdout.write('\001\033[33m\002<<< \001\033[0m\002')
            sys.stdout.flush()
            self.first_content = False

    def _write_thinking(self, text):
        self.thinking_text += text
        self._prefix()
        sys.stdout.write('\001\033[90m\002' + text + '\001\033[0m\002')
        sys.stdout.flush()

    def _write_token(self, text):
        self._prefix()
        sys.stdout.write(text)
        sys.stdout.flush()
        self.content += text

    def _write_token_ansi(self, text, ansi):
        self._prefix()
        sys.stdout.write(f'\001{ansi}\002{text}\001\033[0m\002')
        sys.stdout.flush()
        self.content += text

    def thinking_event(self, content):
        if self.show_thinking:
            self._write_thinking(content)

    def token_event(self, content):
        token = content
        while token:
            if not self.thinking:
                idx = -1
                marker = ''
                for m in ('<thinking>',):
                    pos = token.find(m)
                    if pos != -1 and (idx == -1 or pos < idx):
                        idx = pos
                        marker = m
                if idx != -1:
                    before = token[:idx]
                    if before:
                        self._write_token(before)
                    self._write_thinking(marker)
                    token = token[idx + len(marker):]
                    self.thinking = True
                else:
                    if self.markdown:
                        for text, ansi in self.render_token(token, self.md_state):
                            self._write_token_ansi(text, ansi)
                    else:
                        self._write_token(token)
                    token = ''
            else:
                closer = ''
                closer_pos = -1
                for c in ('</thinking>',):
                    pos = token.find(c)
                    if pos != -1 and (closer_pos == -1 or pos < closer_pos):
                        closer_pos = pos
                        closer = c
                if closer_pos != -1:
                    before = token[:closer_pos]
                    if before:
                        self._write_thinking(before)
                    sys.stdout.write(closer)
                    sys.stdout.flush()
                    token = token[closer_pos + len(closer):]
                    self.thinking = False
                else:
                    self._write_thinking(token)
                    token = ''


class ChatLoop:
    def __init__(self, config: Config):
        self.config = config
        self.provider = None
        self._reinit_provider()

        sessions_dir = config.local_path.parent / 'sessions'
        self.sessions = SessionManager(sessions_dir)
        self.current_session = self.sessions.create()
        self._load_history(config)
        self.registry = CommandRegistry(self)
        register_builtins(self.registry)
        self._setup_readline()

    def _reinit_provider(self):
        from .providers import PROVIDERS, detect_provider
        provider_name = self.config.get('provider', 'ollama')
        factory = PROVIDERS.get(provider_name)
        if factory is None:
            detected = detect_provider(self.config.get('base_url'))
            print(f'Unknown provider "{provider_name}" — using "{detected}" '
                  '(detected from base_url)')
            self.config.set('provider', detected)
            factory = PROVIDERS[detected]

        base_url = self.config.get('base_url')
        model = self.config.get('model')
        if factory.DEFAULT_BASE_URL and base_url:
            for other in PROVIDERS.values():
                if other is not factory and other.DEFAULT_BASE_URL and base_url == other.DEFAULT_BASE_URL:
                    base_url = factory.DEFAULT_BASE_URL
                    break
        if factory.DEFAULT_MODEL and model:
            for other in PROVIDERS.values():
                if other is not factory and other.DEFAULT_MODEL and model == other.DEFAULT_MODEL:
                    model = factory.DEFAULT_MODEL
                    break
        if base_url != self.config.get('base_url'):
            self.config.set('base_url', base_url)
        if model != self.config.get('model'):
            self.config.set('model', model)

        self.provider = factory(
            base_url=base_url,
            api_key=self.config.get('api_key'),
            model=model,
            temperature=self.config.get('temperature'),
            max_tokens=self.config.get('max_tokens'),
        )

    def _load_history(self, config):
        hist = config.local_path.parent / HISTFILE
        if hist.exists():
            try:
                readline.read_history_file(str(hist))
            except OSError:
                pass
        readline.set_history_length(1000)

    def _save_history(self):
        hist = self.config.local_path.parent / HISTFILE
        try:
            hist.parent.mkdir(parents=True, exist_ok=True)
            readline.write_history_file(str(hist))
        except OSError:
            pass

    def _setup_readline(self):
        readline.set_completer(self._completer)
        readline.parse_and_bind('tab: complete')

    def _completer(self, text: str, state: int) -> str | None:
        line = readline.get_line_buffer()
        for prefix in ('/session load ', '/session preview ', '/session delete '):
            if line.startswith(prefix):
                names = [n for n in self.sessions.list() if n.startswith(text)]
                if state < len(names):
                    return names[state] + ' '
                return None
        term = text[1:] if text.startswith('/') else text
        options = sorted(c for c in self.registry.commands if c.startswith(term))
        if state < len(options):
            name = options[state]
            return ('/' + name if text.startswith('/') else name) + ' '
        return None

    def session_auto_save(self):
        if self.current_session and self.current_session.messages:
            self.sessions.save(
                self.current_session,
                tool_max_chars=self.config.get('session_tool_max_chars', 0),
                noise_tools=self.config.get('noise_tools', []),
            )

    def run(self):
        system_prompt = self.config.get('system_prompt', '')
        if system_prompt:
            self.current_session.add_message('system', system_prompt)

        model_str = self.config.get('model', '?')
        provider_str = self.config.get('provider', '?')
        print(f'REPL.io ({provider_str}: {model_str})  /help for commands')

        while True:
            try:
                line = input('\001\033[36m\002>>>\001\033[0m\002 ').strip()
            except (EOFError, KeyboardInterrupt):
                print()
                self.session_auto_save()
                self._save_history()
                break

            if not line:
                continue

            try:
                if line.startswith('/'):
                    self.current_session.add_message('command', line)
                    self.registry.dispatch(line)
                    self.session_auto_save()
                else:
                    self._handle_message(line)
            except Exception as e:
                self.current_session.add_error(0, str(e))
                print(f'\001\033[91m\002[Error]\001\033[0m\002 {e}')

        self._save_history()

    def _agent_loop(self):
        tools_schema = self._init_tooling()
        turn_start = datetime.now(timezone.utc)
        show_thinking = self.config.get('show_thinking', True)
        markdown = self.config.get('markdown_streaming')
        renderer: _StreamRenderer | None = None
        usage = None

        try:
            while True:
                renderer = _StreamRenderer(show_thinking, markdown, self._render_token)
                tool_calls_detected = False
                got_done = False
                messages = self._provider_messages()
                try:
                    for event in self.provider.chat(messages, tools=tools_schema):
                        t = event.get('type', '')
                        if t == 'thinking':
                            renderer.thinking_event(event['content'])
                        elif t == 'token':
                            renderer.token_event(event['content'])
                        elif t == 'tool_calls':
                            tool_calls_detected = True
                            self._execute_tool_calls(event['tool_calls'], renderer.thinking_text)
                            break
                        elif t == 'error':
                            code = event.get('code', '')
                            msg = event.get('message', 'Unknown error')
                            self.current_session.add_error(code, msg)
                            print(f'\001\033[91m\002[Error {code}]\001\033[0m\002 {msg}')
                            return
                        elif t == 'done':
                            got_done = True
                            usage = event.get('usage') or usage
                            reason = event.get('reason', '')
                            if reason == 'length':
                                msg = ('Assistant output truncated: max_tokens limit reached '
                                       f'({self.config.get("max_tokens")})')
                                self.current_session.add_error(0, msg)
                                print('\001\033[93m\002[output truncated — max_tokens reached; '
                                      'use /config max_tokens N]\001\033[0m\002')
                            break
                except Exception as e:
                    self.current_session.add_error(0, f'Agent loop failed: {e}')
                    print(f'\001\033[91m\002[Error]\001\033[0m\002 {e}')
                    break
                if not tool_calls_detected:
                    if not got_done:
                        msg = 'Stream ended before a completion event'
                        self.current_session.add_error(0, msg)
                        print('\001\033[93m\002[warning] ' + msg + '\001\033[0m\002')
                    elif not renderer.content:
                        msg = 'Assistant returned an empty response'
                        self.current_session.add_error(0, msg)
                        print('\001\033[93m\002[warning] ' + msg + '\001\033[0m\002')
                    break
        finally:
            if renderer and renderer.content:
                end = datetime.now(timezone.utc)
                duration = round((end - turn_start).total_seconds(), 1)
                self.current_session.add_message(
                    'assistant', renderer.content,
                    timestamp=end.isoformat(timespec='seconds'),
                    duration=duration,
                    model=self.config.get('model'),
                    provider=self.config.get('provider'),
                    thinking=renderer.thinking_text or None,
                )
                self._print_turn_footer(duration, usage)
            self.session_auto_save()

    def _print_turn_footer(self, duration: float, usage: dict | None = None):
        if self.config.get('show_context_size', True):
            tokens = self._context_tokens(usage)
            print(f'\001\033[90m\002({duration:.1f}s, {tokens:,} tokens)\001\033[0m\002')
        else:
            print(f'\001\033[90m\002({duration:.1f}s)\001\033[0m\002')

    def _execute_tool_calls(self, tcs: list[dict], thinking: str = ''):
        self.current_session.add_message(
            'assistant', None,
            tool_calls=tcs,
            thinking=thinking or None,
        )
        for tc in tcs:
            name = tc['function']['name']
            try:
                args = json.loads(tc['function']['arguments'])
            except (json.JSONDecodeError, KeyError):
                args = {}
            if (self.config.get('query_refine')
                    and self._tool_registry.refine_required(name)
                    and len(args.get('query', '').split()) <= self.config.get('query_refine_min_words', 3)):
                original = args['query']
                args['query'] = self._refine_query(args['query'])
                if args['query'] != original:
                    print(f'\001\033[90m\002[refine: "{original}" → "{args["query"]}"]\001\033[0m\002')
            output = self._run_tool(name, args)
            analysis = None
            if (self.config.get('tool_analysis')
                    and output and not output.startswith(('[cancelled]', 'Error'))):
                analysis = self._analyze_tool_result(name, output)
            self.current_session.add_message(
                'tool', output,
                tool_call_id=tc['id'],
                tool=name,
                analysis=analysis,
            )

    def _analyze_tool_result(self, name: str, output: str) -> str | None:
        sys_prompt = (
            "You write one-line insights for a session log. Given a tool name and its raw "
            "result, state in a single sentence what useful information the result provided — "
            "so a reader of the log can reconstruct the key insight without re-running the tool. "
            "Return only that sentence, nothing else."
        )
        try:
            result = self.provider.chat_nonstreaming(
                [
                    {'role': 'system', 'content': sys_prompt},
                    {'role': 'user', 'content': f'Tool: {name}\n\nResult:\n{output[:2000]}'},
                ],
                tools=None,
            )
        except Exception:
            return None
        content = result.get('content')
        if not isinstance(content, str):
            return None
        content = content.strip()
        return content or None

    def _perform_search(self, query: str, silent: bool = False) -> str | None:
        from .web.search import search as web_search
        from .web.display import format_results, format_context

        num = self.config.get('search_results', 5)
        results = web_search(query, num)

        if not results:
            if not silent:
                print('\001\033[90m\002(no search results)\001\033[0m\002')
            return None

        if not silent:
            print()
            print(format_results(query, results))

        return format_context(query, results)

    def _init_tooling(self):
        if not self.config.get('tool_calling'):
            self._tool_registry = None
            self._tool_policy = None
            return None
        from .tools.registry import ToolRegistry
        from .tools.builtins import register_tools
        from .tools.machine import register_machine_tools
        from .tools.policy import ToolPolicy
        self._tool_registry = ToolRegistry()
        register_tools(self._tool_registry)
        register_machine_tools(self._tool_registry)
        self._tool_policy = ToolPolicy(
            permissions=self.config.get('tool_permission', {}),
            allow=self.config.get('tools.allow', []),
            deny=self.config.get('tools.deny', []),
            worktree=self.config.local_path.parent.parent,
        )
        allowed = {n for n in self._tool_registry.names()
                   if self._tool_policy.allowed(n)}
        return self._tool_registry.schema_filtered(allowed)

    def _run_tool(self, name: str, args: dict) -> str:
        registry = self._tool_registry
        policy = self._tool_policy
        path_arg = registry.path_arg_for(name)
        path = args.get(path_arg) if path_arg else None
        action = policy.action(name, registry.permission_for(name), path)
        if action == 'deny':
            return f'Error: tool "{name}" is disabled by tool policy'
        if action == 'ask':
            if not self._confirm_tool(name, args):
                return f'[cancelled] User declined the {name} call'
        if self.config.get('tool_status_visible', True):
            self._show_tool_status(name, args)
        return registry.execute(name, args)

    def _confirm_tool(self, name: str, args: dict) -> bool:
        key_arg = self._tool_registry.key_arg_for(name)
        label = name
        if key_arg and args.get(key_arg):
            value = str(args[key_arg])
            label = f'{name} {value[:80]}'
        try:
            answer = input(
                f'\001\033[90m\002  ↳ {label} — approve? [y/N] \001\033[0m\002'
            ).strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return False
        return answer in ('y', 'yes')

    def _show_tool_status(self, name, arguments):
        args_str = ', '.join(f'{k}={v!r}' for k, v in arguments.items())
        print(f'\001\033[90m\002[{name}: {args_str}]\001\033[0m\002')

    def _refine_query(self, query: str) -> str:
        context_count = self.config.get('query_refine_context', 4)
        context_msgs = self._provider_messages()[-context_count:] if context_count > 0 else []
        refine_sys = "You are a search query optimizer. Rewrite the user's query to be more specific and standalone based on the conversation context. Return ONLY the rewritten query, nothing else."
        refined = self.provider.chat_nonstreaming(
            [{'role': 'system', 'content': refine_sys}] + context_msgs + [{'role': 'user', 'content': query}],
            tools=None,
        )
        refined_query = (refined.get('content') or query).strip().strip('"\'')
        return refined_query if refined_query else query

    def _provider_messages(self) -> list[dict]:
        msgs = self.current_session.messages
        boundary = 0
        summary = None
        for m in msgs:
            if m.get('role') == 'command' and m.get('result'):
                summary = m['result']
                from_idx = m.get('compact_from')
                if isinstance(from_idx, int) and from_idx > boundary:
                    boundary = from_idx
        out = []
        if summary:
            out.append({
                'role': 'system',
                'content': 'Summary of earlier conversation:\n\n' + summary,
            })
        declared: set[str] = set()
        for m in msgs[boundary:]:
            role = m.get('role')
            if role == 'command':
                continue
            if role == 'assistant':
                tcs = m.get('tool_calls') or []
                if tcs:
                    declared.update(tc.get('id') for tc in tcs if tc.get('id'))
                    out.append(m)
                else:
                    out.append(m)
            elif role == 'tool':
                if m.get('tool_call_id') in declared:
                    out.append(m)
            else:
                out.append(m)
        return out

    def _clean_messages(self, msgs: list[dict]) -> list[dict]:
        out = []
        for m in msgs:
            role = m.get('role')
            if role == 'command':
                if m.get('result'):
                    out.append({
                        'role': 'system',
                        'content': 'Summary of earlier conversation:\n\n' + m['result'],
                    })
                continue
            if role == 'assistant':
                content = m.get('content')
                if m.get('tool_calls'):
                    if content:
                        out.append({'role': 'assistant', 'content': content})
                    continue
                out.append(m)
            elif role == 'tool':
                out.append({'role': 'user', 'content': f"[tool result] {m.get('content') or ''}"})
            else:
                out.append(m)
        return out

    def _summarize(self, msgs: list[dict]) -> str | None:
        clean = self._clean_messages(msgs)
        prompt = (
            "Summarize the conversation up to this point into a concise summary that "
            "preserves key facts, decisions, tool findings, and open questions. "
            "The summary will be the only remaining record of the earlier conversation. "
            "Return only the summary text, nothing else."
        )
        try:
            result = self.provider.chat_nonstreaming(
                [{'role': 'system', 'content': prompt}] + clean,
                tools=None,
            )
        except Exception:
            result = {'error': {'code': 0, 'message': 'Compaction request failed'}}
        if isinstance(result, dict) and result.get('error'):
            err = result['error']
            code = err.get('code', '')
            msg = err.get('message', 'Unknown error')
            print(f'\001\033[91m\002[Error {code}]\001\033[0m\002 {msg}')
            print('Compaction failed — context unchanged')
            return None
        summary = (result.get('content') or '').strip()
        if not summary:
            print('Compaction failed — context unchanged')
            return None
        return summary

    def compact_session(self):
        keep = max(0, int(self.config.get('compact_keep', 4)))
        msgs = self.current_session.messages
        if not msgs:
            print('Nothing to compact')
            return
        record_idx = len(msgs) - 1 if msgs[-1].get('role') == 'command' else None
        base = msgs[:record_idx] if record_idx is not None else msgs
        boundary = max(0, len(base) - keep) if keep else 0
        summarize = base[:boundary]
        if not summarize:
            print('Nothing to compact')
            return
        summary = self._summarize(summarize)
        if summary is None:
            return
        if record_idx is None:
            self.current_session.add_message('command', '/compact')
            record_idx = len(self.current_session.messages) - 1
        record = self.current_session.messages[record_idx]
        record['result'] = summary
        record['compact_from'] = boundary
        n, chars = self._context_size()
        print(f'Compacted — context now {n} messages ({self._human_chars(chars)})')
        print('--- earlier conversation ---')
        print(summary)
        self.session_auto_save()

    def _context_size(self) -> tuple[int, int]:
        msgs = self._provider_messages()
        chars = sum(len(m.get('content') or '') for m in msgs)
        return len(msgs), chars

    def _context_tokens(self, usage: dict | None = None) -> int:
        if isinstance(usage, dict):
            prompt = usage.get('prompt_tokens')
            if isinstance(prompt, int) and prompt > 0:
                return prompt
        msgs = self._provider_messages()
        chars = sum(len(m.get('content') or '') for m in msgs)
        return max(1, chars // 4)

    def _human_chars(self, n: int) -> str:
        if n >= 1_000_000:
            return f'{n / 1_000_000:.1f}M'
        if n >= 1_000:
            return f'{n / 1_000:.1f}k'
        return str(n)

    def preview_session(self, name: str, session=None):
        s = session if session is not None else self.sessions.read(name)
        if s is None:
            return None
        counts: dict[str, int] = {}
        for m in s.messages:
            role = m.get('role', '?')
            counts[role] = counts.get(role, 0) + 1
        tools = sorted({tc.get('function', {}).get('name', '?')
                        for m in s.messages if m.get('tool_calls')
                        for tc in m['tool_calls']})
        print(f'  {s.name} — {len(s.messages)} messages')
        print(f'    created {s.created_at} · updated {s.updated_at}')
        print('    roles: ' + ' · '.join(f'{k} {v}' for k, v in counts.items()))
        if tools:
            print('    tools: ' + ', '.join(tools))
        return s

    def _render_token(self, token: str, state: dict) -> list[tuple[str, str]]:
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

    def _handle_message(self, content):
        now = datetime.now(timezone.utc)
        self.current_session.add_message(
            'user', content, timestamp=now.isoformat(timespec='seconds')
        )
        self.session_auto_save()

        user_msgs = [m for m in self.current_session.messages if m['role'] == 'user']
        if len(user_msgs) == 1:
            ts = self.current_session.name
            truncated = content[:40]
            space = truncated.rfind(' ')
            if space > 0:
                truncated = truncated[:space]
            msg_part = ''.join(c if c.isalnum() or c in '-_ ' else '' for c in truncated).strip().replace(' ', '_')
            if msg_part:
                old = self.sessions.sessions_dir / f'{self.current_session.name}.json'
                self.current_session.name = f'{ts}_{msg_part.lower()}'
                new = self.sessions.sessions_dir / f'{self.current_session.name}.json'
                if old.exists() and old != new:
                    old.rename(new)
                    self.session_auto_save()

        if self.config.get('tool_calling'):
            self._agent_loop()
        elif self.config.get('web_search'):
            context = self._perform_search(content, silent=True)
            if context:
                self.current_session.add_message('system', context)
            else:
                print('\001\033[90m\002(Skipping AI — no search results)\001\033[0m\002')
                return
            self._agent_loop()
        else:
            self._agent_loop()
