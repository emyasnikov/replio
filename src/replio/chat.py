import sys
import json
import readline
import os
from datetime import datetime, timezone

from .config import Config
from .providers.ollama import OllamaProvider
from .sessions.manager import SessionManager
from .commands.registry import CommandRegistry
from .commands.builtins import register_builtins

HISTFILE = '.replio_history'


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
        provider_name = self.config.get('provider', 'ollama')
        if provider_name == 'ollama':
            self.provider = OllamaProvider(
                base_url=self.config.get('base_url'),
                api_key=self.config.get('api_key'),
                model=self.config.get('model'),
                temperature=self.config.get('temperature'),
                max_tokens=self.config.get('max_tokens'),
            )
        else:
            print(f'Unknown provider "{provider_name}", falling back to ollama')
            self.config.set('provider', 'ollama')
            self._reinit_provider()

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
        commands = sorted(set(self.registry.commands.keys()))

        def completer(text, state):
            if text.startswith('/'):
                options = [c for c in commands if c.startswith(text)]
                if state < len(options):
                    return options[state] + ' '
            return None

        readline.set_completer(completer)
        readline.parse_and_bind('tab: complete')

    def session_auto_save(self):
        if self.current_session and self.current_session.messages:
            self.sessions.save(self.current_session)

    def run(self):
        system_prompt = self.config.get('system_prompt', '')
        if system_prompt:
            self.current_session.add_message('system', system_prompt)

        model_str = self.config.get('model', '?')
        print(f'REPL.io  |  model: {model_str}  |  /help for commands')

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

            if line.startswith('/'):
                self.current_session.add_message('command', line)
                self.registry.dispatch(line)
                self.session_auto_save()
            else:
                self._handle_message(line)

        self._save_history()

    def _stream_response(self) -> str | None:
        messages = self.current_session.messages
        full_response = ''
        start = datetime.now(timezone.utc)
        first_token = True

        for event in self.provider.chat(messages):
            t = event.get('type', '')
            if t == 'token':
                if first_token:
                    sys.stdout.write('\001\033[33m\002<<< \001\033[0m\002')
                    sys.stdout.flush()
                    first_token = False
                token = event['content']
                sys.stdout.write(token)
                sys.stdout.flush()
                full_response += token
            elif t == 'error':
                code = event.get('code', '')
                msg = event.get('message', 'Unknown error')
                print(f'\001\033[91m\002[Error {code}]\001\033[0m\002 {msg}')
                return None
            elif t == 'done':
                elapsed = (datetime.now(timezone.utc) - start).total_seconds()
                print()
                print(f'\001\033[90m\002({elapsed:.1f}s)\001\033[0m\002')
                break

        if full_response:
            end = datetime.now(timezone.utc)
            duration = (end - start).total_seconds()
            self.current_session.add_message(
                'assistant', full_response,
                timestamp=end.isoformat(timespec='seconds'),
                duration=round(duration, 1),
                model=self.config.get('model'),
                provider=self.config.get('provider'),
            )
            self.session_auto_save()

        return full_response

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
            return None
        from .tools.registry import ToolRegistry
        from .tools.builtins import register_tools
        self._tool_registry = ToolRegistry()
        register_tools(self._tool_registry)
        return self._tool_registry.schema()

    def _show_tool_status(self, name, arguments):
        args_str = ', '.join(f'{k}={v!r}' for k, v in arguments.items())
        print(f'\001\033[90m\002[{name}: {args_str}]\001\033[0m\002')

    def _output_content(self, content):
        end = datetime.now(timezone.utc)
        elapsed = round((end - self._response_start).total_seconds(), 1)

        print(f'\001\033[33m\002<<<\001\033[0m\002 {content}')
        print(f'\001\033[90m\002({elapsed:.1f}s)\001\033[0m\002')

        self.current_session.add_message(
            'assistant', content,
            timestamp=end.isoformat(timespec='seconds'),
            duration=elapsed,
            model=self.config.get('model'),
            provider=self.config.get('provider'),
        )
        self.session_auto_save()

    def _refine_query(self, query: str) -> str:
        context_count = self.config.get('query_refine_context', 4)
        context_msgs = self.current_session.messages[-context_count:] if context_count > 0 else []
        refine_sys = "You are a search query optimizer. Rewrite the user's query to be more specific and standalone based on the conversation context. Return ONLY the rewritten query, nothing else."
        refined = self.provider.chat_nonstreaming(
            [{'role': 'system', 'content': refine_sys}] + context_msgs + [{'role': 'user', 'content': query}],
            tools=None,
        )
        refined_query = (refined.get('content') or query).strip().strip('"\'')
        return refined_query if refined_query else query

    def _chat_with_tools(self, force_search: str | None = None):
        messages = self.current_session.messages
        tools_schema = self._init_tooling()
        self._response_start = datetime.now(timezone.utc)

        if force_search:
            context = self._perform_search(force_search, silent=False)
            if context:
                messages.append({
                    'role': 'tool',
                    'tool_call_id': 'forced',
                    'content': context,
                })

        while True:
            result = self.provider.chat_nonstreaming(messages, tools=tools_schema)

            if 'error' in result:
                err = result['error']
                print(f'\001\033[91m\002[Error {err["code"]}]\001\033[0m\002 {err["message"]}')
                break

            tcs = result.get('tool_calls')
            if tcs:
                messages.append({
                    'role': 'assistant',
                    'content': result.get('content'),
                    'tool_calls': tcs,
                })
                for tc in tcs:
                    name = tc['function']['name']
                    args = json.loads(tc['function']['arguments'])
                    if (self.config.get('query_refine')
                            and name == 'web_search'
                            and len(args.get('query', '').split()) <= self.config.get('query_refine_min_words', 3)):
                        original = args['query']
                        args['query'] = self._refine_query(args['query'])
                        if args['query'] != original:
                            print(f'\001\033[90m\002[refine: "{original}" → "{args["query"]}"]\001\033[0m\002')
                    if self.config.get('tool_status_visible', True):
                        self._show_tool_status(name, args)
                    output = self._tool_registry.execute(name, args)
                    messages.append({
                        'role': 'tool',
                        'tool_call_id': tc['id'],
                        'content': output,
                    })
                continue

            content = result.get('content', '')
            if content:
                self._stream_response()
            break

    def _handle_message(self, content):
        now = datetime.now(timezone.utc)
        self.current_session.add_message(
            'user', content, timestamp=now.isoformat(timespec='seconds')
        )
        self.session_auto_save()

        if self.config.get('tool_calling'):
            self._chat_with_tools()
        elif self.config.get('web_search'):
            context = self._perform_search(content, silent=True)
            if context:
                self.current_session.add_message('system', context)
            else:
                print('\001\033[90m\002(Skipping AI — no search results)\001\033[0m\002')
                return
            self._stream_response()
        else:
            self._stream_response()
