import json
import time
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .config import Config
from .sessions.manager import SessionManager
from .commands.registry import CommandRegistry
from .commands.builtins import register_builtins
from .plugins.manager import PluginManager
from .ui import NullUI


@dataclass
class TurnResult:
    content: str | None = None
    thinking: str | None = None
    tool_calls: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    duration: float = 0.0
    usage: dict | None = None
    model: str = ''
    provider: str = ''
    session: str = ''
    status: str = 'ok'

    def to_dict(self) -> dict:
        return {
            'content': self.content,
            'thinking': self.thinking,
            'tool_calls': self.tool_calls,
            'errors': self.errors,
            'duration': self.duration,
            'usage': self.usage,
            'model': self.model,
            'provider': self.provider,
            'session': self.session,
            'status': self.status,
        }


CONTINUE_INSTRUCTION = ('Continue exactly where you stopped. '
                        'Do not repeat what was already written.')


class Engine:
    def __init__(self, config: Config, ui=None):
        self.config = config
        self._ui = ui
        self._plugin_manager = PluginManager(config)
        self._plugin_manager.load()
        self._reinit_provider()
        sessions_dir = config.local_path.parent / 'sessions'
        self.sessions = SessionManager(sessions_dir)
        self.current_session = self.sessions.create()
        self.registry = CommandRegistry(self)
        register_builtins(self.registry)
        self._plugin_manager.register_commands(self.registry)

    @property
    def ui(self):
        if getattr(self, '_ui', None) is None:
            self._ui = NullUI()
        return self._ui

    @property
    def models(self):
        if getattr(self, '_models', None) is None:
            from .models import ModelRegistry
            self._models = ModelRegistry()
        return self._models

    def _resolve_provider_factory(self, provider: str, base_url: str):
        from .providers import PROVIDERS, detect_provider
        merged = dict(PROVIDERS)
        plugin_manager = getattr(self, '_plugin_manager', None)
        if plugin_manager is not None:
            merged.update(plugin_manager.provider_classes())
        factory = merged.get(provider)
        if factory is not None:
            return factory, provider, merged
        detected = detect_provider(base_url)
        self.ui.info(f'Unknown provider "{provider}" - using "{detected}" '
                     '(detected from base_url)')
        return merged.get(detected), detected, merged

    def _reinit_provider(self):
        provider_name = self.config.get('provider', 'ollama')
        factory, resolved, merged = self._resolve_provider_factory(
            provider_name, self.config.get('base_url'))
        if factory is None:
            return
        if resolved != provider_name:
            self.config.apply('provider', resolved)
            provider_name = resolved

        base_url = self.config.get('base_url')
        model = self.config.get('model')
        if factory.DEFAULT_BASE_URL and base_url:
            for other in merged.values():
                if other is not factory and other.DEFAULT_BASE_URL and base_url == other.DEFAULT_BASE_URL:
                    base_url = factory.DEFAULT_BASE_URL
                    break
        if factory.DEFAULT_MODEL and model:
            for other in merged.values():
                if other is not factory and other.DEFAULT_MODEL and model == other.DEFAULT_MODEL:
                    model = factory.DEFAULT_MODEL
                    break
        if base_url != self.config.get('base_url'):
            self.config.apply('base_url', base_url)
        if model != self.config.get('model'):
            self.config.apply('model', model)

        api_key = self.config.get('api_key')
        entry = self.models.find(provider_name, base_url, model)
        if entry is not None and entry.api_key:
            api_key = entry.api_key

        self.provider = factory(
            base_url=base_url,
            api_key=api_key,
            model=model,
            temperature=self.config.get('temperature'),
            max_tokens=self.config.get('max_tokens'),
            reasoning=self.config.get('reasoning'),
        )

    def check_connection(self, base_url: str | None = None, api_key: str | None = None,
                         model: str | None = None,
                         provider: str | None = None) -> tuple[bool, str, list[str]]:
        from .providers.base import _connection_message
        provider = provider or self.config.get('provider')
        base_url = self.config.get('base_url') if base_url is None else base_url
        api_key = self.config.get('api_key') if api_key is None else api_key
        model = model or self.config.get('model')
        factory, _, _ = self._resolve_provider_factory(provider, base_url)
        if factory is None:
            return False, f'No provider registered for "{provider}"', []
        probe = factory(base_url=base_url, api_key=api_key, model=model)
        models, error = probe._fetch_models()
        if error:
            return False, error, []
        return True, _connection_message(models, model), models

    def list_models(self, provider: str | None = None,
                    base_url: str | None = None,
                    api_key: str | None = None,
                    model: str | None = None) -> tuple[list[str], str | None]:
        provider = provider or self.config.get('provider')
        base_url = self.config.get('base_url') if base_url is None else base_url
        api_key = self.config.get('api_key') if api_key is None else api_key
        model = self.config.get('model') if model is None else model
        factory, _, _ = self._resolve_provider_factory(provider, base_url)
        if factory is None:
            return [], f'No provider registered for "{provider}"'
        probe = factory(base_url=base_url, api_key=api_key, model=model)
        return probe._fetch_models()

    def session_auto_save(self):
        if self.current_session and self.current_session.messages:
            self.sessions.save(
                self.current_session,
                tool_max_chars=self.config.get('session_tool_max_chars', 0),
                noise_tools=self.config.get('noise_tools', []),
            )

    def load_or_create_session(self, name: str | None = None):
        if name and self.sessions.read(name) is not None:
            self.current_session = self.sessions.load(name)
        elif name:
            self.current_session = self.sessions.create(name)
        else:
            self.current_session = self.sessions.create()
        return self.current_session

    def chat(self, text: str, autoname: bool = True) -> TurnResult:
        now = datetime.now(timezone.utc)
        self.current_session.add_message(
            'user', text, timestamp=now.isoformat(timespec='seconds')
        )
        self.session_auto_save()

        if autoname:
            self._auto_name_session(text)

        if self.config.get('tool_calling'):
            return self._agent_loop()
        if self.config.get('web_search'):
            context = self._perform_search(text, silent=True)
            if context:
                self.current_session.add_message('system', context)
            else:
                self.ui.info('(Skipping AI - no search results)')
                return TurnResult(status='empty', session=self.current_session.name)
        return self._agent_loop()

    def _auto_name_session(self, content: str):
        user_msgs = [m for m in self.current_session.messages if m['role'] == 'user']
        if len(user_msgs) != 1:
            return
        ts = self.current_session.name
        truncated = content[:40]
        space = truncated.rfind(' ')
        if space > 0:
            truncated = truncated[:space]
        msg_part = ''.join(c for c in unicodedata.normalize('NFKD', truncated)
                           if c.isascii() and (c.isalnum() or c in '-_ ')).strip().replace(' ', '_')
        if not msg_part:
            return
        old = self.sessions.sessions_dir / f'{self.current_session.name}.json'
        self.current_session.name = f'{ts}_{msg_part.lower()}'
        new = self.sessions.sessions_dir / f'{self.current_session.name}.json'
        if old.exists() and old != new:
            old.rename(new)
            self.session_auto_save()

    def _agent_loop(self) -> TurnResult:
        tools_schema = self._init_tooling()
        turn_start = datetime.now(timezone.utc)
        usage = None
        status = 'ok'
        content = ''
        thinking = ''
        executed_tool_calls: list[dict] = []
        err_base = len(self.current_session.errors)

        try:
            while True:
                think_start: datetime | None = None

                def feed_thinking(text):
                    nonlocal think_start
                    if think_start is None:
                        think_start = datetime.now(timezone.utc)
                        self.ui.thinking_begin()
                    self.ui.thinking(text)

                def end_thinking():
                    nonlocal think_start
                    if think_start is not None:
                        dur = round((datetime.now(timezone.utc) - think_start)
                                    .total_seconds(), 1)
                        think_start = None
                        self.ui.thinking_end(dur)

                messages = self._provider_messages()
                max_attempts = 1 + max(0, int(self.config.get('stream_retries', 2)))
                retry_delay = max(0.0, float(self.config.get('stream_retry_delay', 0.5)))
                auto_continue = self.config.get('auto_continue', True)
                max_continues = max(0, int(self.config.get('auto_continue_max', 2)))
                content = ''
                thinking = ''
                attempt = 1
                consumes = 0
                while True:
                    stream_messages = messages
                    if consumes > 0:
                        stream_messages = self._provider_messages() + [
                            {'role': 'assistant', 'content': content},
                            {'role': 'user', 'content': CONTINUE_INSTRUCTION},
                        ]
                    s_content = ''
                    s_thinking = ''
                    in_thinking = False
                    tool_calls_detected = False
                    got_done = False
                    aborted = False
                    try:
                        for event in self.provider.chat(stream_messages, tools=tools_schema):
                            t = event.get('type', '')
                            if t == 'thinking':
                                s_thinking += event['content']
                                feed_thinking(event['content'])
                            elif t == 'token':
                                token = event['content']
                                while token:
                                    if not in_thinking:
                                        marker = '<thinking>'
                                        idx = token.find(marker)
                                        if idx != -1:
                                            before = token[:idx]
                                            if before:
                                                end_thinking()
                                                s_content += before
                                                self.ui.token(before)
                                            s_thinking += marker
                                            feed_thinking(marker)
                                            token = token[idx + len(marker):]
                                            in_thinking = True
                                        else:
                                            end_thinking()
                                            s_content += token
                                            self.ui.token(token)
                                            token = ''
                                    else:
                                        closer = '</thinking>'
                                        idx = token.find(closer)
                                        if idx != -1:
                                            before = token[:idx]
                                            if before:
                                                s_thinking += before
                                                feed_thinking(before)
                                            end_thinking()
                                            token = token[idx + len(closer):]
                                            in_thinking = False
                                        else:
                                            s_thinking += token
                                            feed_thinking(token)
                                            token = ''
                            elif t == 'tool_calls':
                                tool_calls_detected = True
                                end_thinking()
                                executed_tool_calls += self._execute_tool_calls(
                                    event['tool_calls'], s_thinking or None)
                                break
                            elif t == 'error':
                                code = event.get('code', '')
                                msg = event.get('message', 'Unknown error')
                                end_thinking()
                                self.current_session.add_error(code, msg)
                                self.ui.error(code, msg)
                                status = 'error'
                                aborted = True
                                break
                            elif t == 'done':
                                got_done = True
                                usage = event.get('usage') or usage
                                reason = event.get('reason', '')
                                end_thinking()
                                break
                    except Exception as e:
                        end_thinking()
                        content += s_content
                        thinking += s_thinking
                        self.current_session.add_error(0, f'Agent loop failed: {e}')
                        self.ui.error(0, str(e))
                        status = 'error'
                        aborted = True
                    if aborted:
                        break
                    if tool_calls_detected:
                        break
                    content += s_content
                    thinking += s_thinking
                    if got_done:
                        if reason == 'length':
                            if content and auto_continue and consumes < max_continues:
                                consumes += 1
                                attempt = 1
                                self.ui.info(f'(output truncated - continuing '
                                             f'{consumes}/{max_continues})')
                                continue
                            limit = self.config.get('max_tokens')
                            if limit > 0:
                                msg = ('Assistant output truncated: max_tokens limit reached '
                                       f'({limit})')
                                self.ui.warning('Assistant output truncated (max_tokens reached); '
                                                'use /config max_tokens N')
                            else:
                                msg = ("Assistant output truncated: the provider's default "
                                       'max_tokens limit was reached')
                                self.ui.warning('Assistant output truncated (provider max_tokens '
                                                'limit reached); set /config max_tokens N to raise it')
                            self.current_session.add_error(0, msg)
                            status = 'truncated'
                            break
                        if not content and not thinking:
                            if attempt < max_attempts:
                                attempt += 1
                                if retry_delay:
                                    time.sleep(retry_delay)
                                continue
                            msg = 'Assistant returned an empty response'
                            self.current_session.add_error(0, msg)
                            self.ui.warning(msg)
                            status = 'empty'
                        break
                    if not content and attempt < max_attempts:
                        self.ui.info(f'(stream ended before a completion event - retrying '
                                     f'{attempt}/{max_attempts - 1})')
                        attempt += 1
                        if retry_delay:
                            time.sleep(retry_delay)
                        continue
                    msg = 'Stream ended before a completion event'
                    self.current_session.add_error(0, msg)
                    if executed_tool_calls:
                        self.ui.warning(f'{msg} - tool results are saved, '
                                        'send "continue" to retry the answer')
                    else:
                        self.ui.warning(msg)
                    status = 'error'
                    break
                if aborted or not tool_calls_detected:
                    break
        finally:
            if content or thinking:
                end = datetime.now(timezone.utc)
                duration = round((end - turn_start).total_seconds(), 1)
                self.current_session.add_message(
                    'assistant', content,
                    timestamp=end.isoformat(timespec='seconds'),
                    duration=duration,
                    model=self.config.get('model'),
                    provider=self.config.get('provider'),
                    thinking=thinking or None,
                    reasoning=self.config.get('reasoning'),
                    mode=self.config.get('mode'),
                )
                self.ui.footer(duration, usage, self._context_tokens(usage))
            self.session_auto_save()

        duration = round((datetime.now(timezone.utc) - turn_start).total_seconds(), 1)
        return TurnResult(
            content=content or None,
            thinking=thinking or None,
            tool_calls=executed_tool_calls,
            errors=self.current_session.errors[err_base:],
            duration=duration,
            usage=usage,
            model=self.config.get('model'),
            provider=self.config.get('provider'),
            session=self.current_session.name,
            status=status,
        )

    def _execute_tool_calls(self, tcs: list[dict], thinking: str = '') -> list[dict]:
        self.current_session.add_message(
            'assistant', None,
            tool_calls=tcs,
            thinking=thinking or None,
            reasoning=self.config.get('reasoning'),
            mode=self.config.get('mode'),
        )
        executed: list[dict] = []
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
                    self.ui.tool_refine(original, args['query'])
            output = self._run_tool(name, args)
            if (self.config.get('tool_status_visible', True)
                    and self._tool_registry.echo_for(name) and output
                    and not output.startswith(('[cancelled]', 'Error'))):
                self.ui.tool_result(output)
            executed.append({'name': name, 'arguments': args})
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
        return executed

    def _analyze_tool_result(self, name: str, output: str) -> str | None:
        sys_prompt = (
            "You write one-line insights for a session log. Given a tool name and its raw "
            "result, state in a single sentence what useful information the result provided - "
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
        pm = getattr(self, '_plugin_manager', None)
        service = pm.service('search') if pm is not None else None
        if service is None:
            if not silent:
                self.ui.info('(web search unavailable - replio-core-websearch plugin not loaded)')
            return None

        num = self.config.get('search_results', 5)
        results = service.search(query, num)

        if not results:
            if not silent:
                self.ui.info('(no search results)')
            return None

        if not silent:
            self.ui.info('')
            self.ui.info(service.display(query, results))

        return service.context(query, results)

    def _init_tooling(self):
        if not self.config.get('tool_calling'):
            self._tool_registry = None
            self._tool_policy = None
            return None
        from .tools.registry import ToolRegistry
        from .tools.policy import ToolPolicy
        from .modes import merge_policy
        self._tool_registry = ToolRegistry()
        plugin_manager = getattr(self, '_plugin_manager', None)
        if plugin_manager is not None:
            plugin_manager.register_tools(self._tool_registry)
        permissions, allow, deny = merge_policy(self.config)
        self._tool_policy = ToolPolicy(
            permissions=permissions,
            allow=allow,
            deny=deny,
            worktree=self.config.local_path.parent.parent,
        )
        allowed = {n for n in self._tool_registry.names()
                   if self._tool_policy.allowed(
                       n, self._tool_registry.permission_for(n))}
        return self._tool_registry.schema_filtered(allowed)

    def _run_tool(self, name: str, args: dict) -> str:
        registry = self._tool_registry
        policy = self._tool_policy
        cleaned = registry.clean_args(name, args)
        path_arg = registry.path_arg_for(name)
        path = cleaned.get(path_arg) if path_arg else None
        action = policy.action(name, registry.permission_for(name), path)
        if action == 'deny':
            return f'Error: tool "{name}" is disabled by tool policy'
        if action == 'ask':
            if not self._confirm_tool(name, args):
                return f'[cancelled] User declined the {name} call'
        if self.config.get('tool_status_visible', True):
            self._show_tool_status(name, args)
        result = registry.execute(name, args, config=self.config)
        if result.startswith('Error') and self.config.get('show_errors', True):
            self.ui.tool_error(result)
        return result

    def _confirm_tool(self, name: str, args: dict) -> bool:
        key_arg = self._tool_registry.key_arg_for(name)
        label = name
        if key_arg and args.get(key_arg):
            value = str(args[key_arg])
            label = f'{name} {value[:80]}'
        params = self._tool_registry.params_str(name, args)
        if params and self.config.get('glyph_params', True):
            label = f'{label} [{params}]'
        return self.ui.confirm(name, label)

    def _show_tool_status(self, name, arguments):
        value, body = self._tool_registry.status_parts(name, arguments)
        activity = self._tool_registry.activity(name, arguments)
        if activity is not None and self.config.get('glyph_lines', True):
            glyph, verb, label, params = activity
            if params and self.config.get('glyph_params', True):
                label = f'{label} [{params}]'
            self.ui.activity(glyph, verb, label, body)
        else:
            self.ui.tool_status(name, value, body)

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
        from .modes import system_instruction
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
        instruction = system_instruction(self.config)
        if instruction:
            out.append({'role': 'system', 'content': instruction})
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
            self.ui.error(code, msg)
            self.ui.info('Compaction failed - context unchanged')
            return None
        summary = (result.get('content') or '').strip()
        if not summary:
            self.ui.info('Compaction failed - context unchanged')
            return None
        return summary

    def compact_session(self):
        keep = max(0, int(self.config.get('compact_keep', 4)))
        msgs = self.current_session.messages
        if not msgs:
            self.ui.info('Nothing to compact')
            return
        record_idx = len(msgs) - 1 if msgs[-1].get('role') == 'command' else None
        base = msgs[:record_idx] if record_idx is not None else msgs
        boundary = max(0, len(base) - keep) if keep else 0
        summarize = base[:boundary]
        if not summarize:
            self.ui.info('Nothing to compact')
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
        self.ui.info(f'Compacted - context now {n} messages ({self._human_chars(chars)})')
        self.ui.info('--- earlier conversation ---')
        self.ui.info(summary)
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
        self.ui.info(f'  {s.name} - {len(s.messages)} messages')
        self.ui.info(f'    created {s.created_at} · updated {s.updated_at}')
        self.ui.info('    roles: ' + ' · '.join(f'{k} {v}' for k, v in counts.items()))
        if tools:
            self.ui.info('    tools: ' + ', '.join(tools))
        return s
