# Changelog

## v0.13.0 - 2026-08-16

- Per-turn stats on their own line — the `(Ns, N tokens)` footer no longer lands at the end of the last content line; `ReplUI` tracks whether streamed output ended with a newline and emits a separating one before the footer
- One-shot retry for empty/truncated streams — a provider stream that ends without a completion event and with no streamed content is requested once more (with a "retrying" note) before the "Stream ended before a completion event" error is surfaced; masks transient provider drops such as Ollama cloud returning an empty follow-up stream after a tool call
- `write_file` status preview ends with a dimmed parenthesized summary — resolved absolute path, line count, char count, and created/overwritten/appended action (tool result string stays minimal)
- Thinking announce — `+ Thinking` on its own line before streamed reasoning when `show_thinking: true`; when hidden, `+ Thought 12.3s` (thinking duration) is printed instead and the reasoning text stays out of the terminal. The engine times the thinking window (`thinking_begin`/`thinking_end` UI hooks), `HeadlessUI` mirrors it in `--verbose` mode, and a spinner (`⠧ Thinking`) can replace the static markers later
- Human-readable tool status — default oneliner is now `[tool: key_arg]` (e.g. `[write_file: test.md]`, `[run_command: echo hi]`) instead of the raw args dump (`content='...\n...', mode='w'`); detail lines follow dimmed: `write_file` shows the written text via a registered `status` callback (new-file `+ line` preview, or a `difflib` unified diff of existing files — works for append too), and `run_command` echoes its output (`echo` registration metadata)
- `list_dir` gains `depth` (default 1) — higher values render an indented recursive tree (`tree -L` style), skipping `SKIP_DIRS` during descent; `depth=1` output is unchanged
- `ToolRegistry.execute()` drops arguments not declared in a tool's schema and `null`-valued arguments (e.g. a hallucinated `recursive`, or `depth: null`) — tools run with their valid args instead of erroring; worktree semantics documented (worktree = launch directory / `--path`; launching from `~` makes home the worktree, so subdirectories don't escalate)
- **Built-in features ship as bundled plugins** — `web_search`/`fetch_page` and the machine tools (read_file, list_dir, write_file, glob, grep, run_command) moved out of the core (`src/replio/web/`, `tools/builtins.py`, `tools/machine.py` deleted) into three first-party bundled plugins under `plugins/` (shipped as `replio.plugins.bundled`): `replio-core-websearch`, `replio-core-fs`, `replio-core-exec`. Packaged via `package-dir` mapping, so the repo-root `plugins/` directory is the canonical source; discovery adds a bundled root with precedence bundled < global < local (local/global overrides win)
- **`plugins` config list** — replaces `plugins.enabled`/`plugins.deny` (migrated automatically). The default config lists the bundled plugins so they are active out of the box; empty list = all discovered plugins load; `/plugins enable/disable` and `install`/`uninstall` maintain the list
- **`register_services` entry hook** — plugins can power core non-tool features. `replio-core-websearch` registers the `search` service backing the `web_search: true` search-then-answer mode (`engine._perform_search` now routes through it and degrades gracefully when the plugin is absent)
- `PluginInfo.origin` (`bundled`/`global`/`local`) shown in `/plugins` and `replio plugins list`; bundled plugins cannot be `update`d or `uninstall`ed (disable instead)
- `tests/test_bundled_plugins.py` (10 tests) — bundled discovery, tool registration, search service, bundled uninstall/update blocking, local override, config disable, default-config membership; `test_tool_registry.py`/`test_machine_tools.py`/`test_commands.py`/`test_tool_calling.py`/`test_session_log.py` reworked to load bundled plugins and patch the search service instead of `replio.web.search`

## v0.12.0 — 2026-08-15

- Plugin system (`src/replio/plugins/`) — external repositories register **tools, providers, and slash commands** without changing the core; `PluginManager` discovers plugins in `~/.config/replio/plugins/` and `.replio/plugins/` (local wins), validates `manifest.json` (`replio_version`/`python` semver ranges), imports entry modules once, and hooks them into the live registries
- Plugin entry contract — optional `register_tools(registry)` / `register_providers(providers)` / `register_commands(commands)` hooks on the entry module, matching the core's `register_*` conventions; plugin tools automatically inherit tool policy, `/tool`, `/help`, refinement, and session logging
- Lazy plugin dependencies — third-party packages are imported inside plugin functions (never by the core), so the stdlib-only guarantee holds and a missing dep surfaces as a tool error with `pip install` guidance
- `/plugins` command (`/plugins list`, `/plugins <name>` detail with per-dep status, `enable`/`disable`, `install`/`update`/`uninstall`) plus tab completion for plugin names; `/connect` now offers plugin providers
- `replio plugins` CLI (`list`/`install`/`update`/`uninstall`) — headless plugin management so `replio run`/CI can use freshly installed plugins; `install` clones a git URL or copies a local path, records `source`, and `--deps` pip-installs the declared `requires`
- Config keys `plugins.enabled` (allowlist; empty = all) and `plugins.deny` (always excluded) — activation is explicit and applies on the next start
- `docs/plugins.md` — plugin layout, manifest schema, compatibility contract, entry hooks, management, security, and future paths (per-plugin venv isolation, PyPI entry-point source, migrating core web tools out)
- `tests/test_plugins.py` (30 tests) — manifest parsing, `replio_version`/`python` compat skipping, enable/deny filtering, global/local precedence, entry load-error isolation, all three registration hooks, lazy-dep pip guidance, tool-policy filtering, install/update/uninstall from a local path, and Engine integration (tools + commands + `/plugins`)
- REPL banner shows the version — `Replio v0.12.0 (provider: model)` on startup; gated by `show_version` config (default `true`), toggleable via `/config show_version false`
- `GET /version` endpoint — the serve API exposes the installed version as `{"version": ...}`, alongside `/health` and `/sessions`
- `/version` slash command (alias `/v`) — prints `Replio <version>` in the REPL; version lookup centralized in `replio.get_version()` and shared with the CLI `--version` flag
- `--version` / `-v` CLI flag — `replio --version` prints the installed version (from package metadata) and exits
- Clear screen on REPL start — the interactive REPL wipes scrollback + visible screen (`\033[3J\033[2J\033[H`) before printing the banner; gated by `clear_screen` config (default `true`), toggleable via `/config clear_screen false`. Headless `run`/`serve` modes are unaffected.

## v0.11.0 — 2026-08-14

- `Engine` headless agent core (`engine.py`) + `TurnResult` — the agent loop extracted from `ChatLoop` returns a structured `{content, thinking, tool_calls, errors, duration, usage, model, provider, session, status}` turn result; `Engine.chat(text, autoname=True)` and `Engine.load_or_create_session(name)` make sessions addressable from any front-end
- `UISink` abstraction (`ui.py`) — the loop renders through `ReplUI` (terminal ANSI streaming, confirm prompts, footer), `HeadlessUI` (stderr diagnostics, auto-approve/deny confirm policy, never blocks on stdin), or `NullUI` (silent)
- `replio run` — one-shot CLI mode (JSON or text output) over the same agent loop + session manager; flags `--prompt`, `--provider`, `--model`, `--base-url`, `--output`, `--verbose`, `--session-id`, `--yes`/`--no`; exits `0` on ok/truncated and `1` on error/empty
- `replio serve` — stdlib `ThreadingHTTPServer` JSON API (`POST /chat`, `GET /sessions`, `GET /health`) with a shared engine serialized behind a lock; ask-gated tools are denied (fed back as `[cancelled]`), the server never blocks on stdin
- Headless `ask` policy — tools gated by `ask` are denied by default in headless mode; `--yes`/`--no` override to approve or deny
- Tests for headless entry points — `test_engine.py` (turn result, thinking split, session addressing, confirm policy), `test_cli.py` (mock provider, JSON/text output, session-id persistence, exit codes), `test_server.py` (ephemeral-port server against a mocked provider)
- `ChatLoop` is now `ChatLoop(Engine)` — a thin REPL shell (readline, banner, prompt loop) inheriting the headless core; commands and session logic are unchanged
- `_handle_message()` replaced by `Engine.chat()`; `_StreamRenderer` moved into `ReplUI`, and the `<thinking>` marker split is owned by the engine so thinking stays separate from content in JSON results
- The `input()` confirm prompt moved from `chat.py` to `ui.py` (tests patch `replio.ui.input`)

## v0.10.0 - 2026-08-13

- OpenAI, Groq, and Anthropic providers (`providers/openai.py`, `providers/groq.py`, `providers/anthropic.py`) — OpenAI-compatible `/v1/chat/completions` subclasses of the shared `OpenAICompatibleProvider`, each with its own default `base_url` and default model (`gpt-4o-mini`, `llama-3.3-70b-versatile`, `claude-sonnet-4-20250514`)
- Provider auto-detection — `detect_provider(base_url)` in `providers/__init__.py` matches well-known hosts (`openai.com`, `groq.com`, `anthropic.com`, `ollama.com`/`ollama.ai`) and falls back to the generic `openai-compatible` provider for any other OpenAI-compatible endpoint
- `PROVIDERS` registry — `_reinit_provider()` resolves the configured provider name through the dict (`ollama`, `openai`, `groq`, `anthropic`, `openai-compatible`); unknown names are auto-detected from `base_url` with a printed note instead of silently falling back to ollama
- `/connect` detects the provider from the entered base URL and switches automatically when it matches a known host
- Agent-loop hardening — streamed content is persisted when the SSE stream ends without a `done` event, and session `errors` entries are recorded for silent failures: stream EOF before a completion event, empty/thinking-only `done`, and unexpected exceptions escaping the agent loop; unexpected exceptions in `run()` are caught, logged to the session `errors`, and the REPL stays alive instead of crashing
- `tests/test_providers.py` — provider defaults, auth header, `detect_provider`, and registry coverage
- `OllamaProvider` now subclasses the shared `OpenAICompatibleProvider` — the streaming/tool-call/error logic it previously owned moved to `providers/base.py`; behavior unchanged
- Switching providers swaps in the new provider's default `base_url`/`model` when the configured values still match another provider's default (i.e. were never customized); explicit custom values are preserved
- `tests/test_ollama_provider.py` — `stream_sse` patches retargeted to the base module where the streaming logic now lives

## v0.9.0 — 2026-08-12

- `/session preview <name>` — read-only structural preview (name, created/updated, message counts by role, tools used) without switching the active session; shown on `/session load` too
- `noise_tools` config (default `["fetch_page"]`) — results of these tools are replaced by a `[<tool> result excluded from log; see tool call above for parameters]` marker at persistence time only; the live turn still feeds the full result to the model, and the assistant `tool_calls` message keeps the query/URL so the log stays reproducible
- Session-name tab completion — `/session load` and `/session delete` complete against saved session names (bash-style common-prefix completion, double-tab lists candidates)
- Compaction summary visibility — `/compact` and `/session load` (when the compaction offer is accepted) print the generated summary text, stored as the `result` of the triggering `command` message (with a `compact_from` boundary index)
- Context-size visibility — dimmed `(Ns, N tokens)` line after each response, using the provider's `usage.prompt_tokens` when reported (fallback: char-based estimate); gated by `show_context_size` (default `true`)
- `/session load` compaction offer — always prompts `Summarize & trim history before continuing? [y/N]`
- `tests/test_http.py` — `stream_sse` survives a multi-byte UTF-8 character split across 4096-byte read chunks, normal data-line flow, and `[DONE]`/error passthrough
- Sessions are **append-only logs** — compaction no longer removes or rewrites session entries; it only trims the provider context via the summary record and boundary, so the full history always stays in the file
- Provider payload is prepared from the log — `role: command` messages are never sent as-is; compaction summary records convert to `system` messages, and dangling tool messages are skipped
- `/session load` and `/session preview` print a structural preview; `/session load` records the load as a `command` message in the loaded session
- `max_tokens` default is now `0` (unset) — the value is omitted from the provider payload entirely, so the provider's own default applies and long answers are no longer cut at the old 2048-token default; set a cap explicitly via `/config max_tokens N`
- `/session new` and `/session load` now reassign `ChatLoop.current_session` — previously they only updated `SessionManager.current`, so loaded/new sessions were never actually used for prompts, rendering, or autosave
- If a configured `max_tokens` cap is hit (`finish_reason: length`), the loop now prints a visible truncation warning and records a session `errors` entry instead of stopping silently
- `OllamaProvider.chat()` streaming captures `usage` from the final chunk and attaches it to the `done` event
- `config.py` — new keys `show_context_size`, `compact_keep` (default `4`), `noise_tools` (default `["fetch_page"]`); removed `compact_prompt_chars`
- Compaction failed with sessions containing `command`/tool messages — the summarizer now sanitizes the batch (drops `command`, drops `tool_calls` declarations, converts `tool` → `user [tool result]`), and provider errors are printed instead of swallowed as a generic "Compaction failed"
- Tab completion for `/` commands never matched — readline passes the current word, and command names have no leading slash, so the prefix test always failed; the completer now strips the `/` when comparing and re-adds it on completion
- `stream_sse` decoded each 4096-byte chunk with strict UTF-8, so a multi-byte character split across a chunk boundary raised `UnicodeDecodeError` — caught as a generic error that aborted the stream mid-output and killed the tool loop during long web research; buffering is now byte-based and each complete line is decoded with `errors='replace'`

## v0.8.0 — 2026-08-05

- `Session` metadata — `created_at`/`updated_at` (bumped on every message) and a top-level `errors` array with `add_error()`; `to_dict()` now persists **every** message, including `role: tool`
- `tool_analysis` config (default `false`) — optional model-generated one-line insight summary stored as `analysis` on each tool message, so a session log can be reconstructed without re-running the tool; skipped for `[cancelled]`/error results
- `session_tool_max_chars` config (default `0` = unlimited) — caps persisted tool-result content at serialization time only; the in-memory provider context always keeps full results
- `_StreamRenderer` captures `thinking_text`; `_agent_loop` persists per-round reasoning as `thinking` metadata on tool-call and final assistant messages (still excluded from `content`)
- Provider `error` events now append to the session `errors` array before the loop bails, instead of being dropped
- `tests/test_session_log.py` — session model, save/load round-trip, legacy-file loading, `tool_max_chars` truncation, thinking metadata, and `tool_analysis` behavior
- `SessionManager.save()` accepts `tool_max_chars`; `session_auto_save()` forwards the config value
- `_execute_tool_calls()` appends assistant tool-call and tool-result messages via `Session.add_message()` (single timestamp/`updated_at` path instead of direct list appends)
- Docs updated to match: session files are now complete logs (tool results, thinking, errors); confirm prompts and tool status remain ephemeral UI

## v0.7.0 — 2026-08-03

- Tool `short=` registration metadata — human-readable one-line labels for the `/help` tools table (falls back to a truncated `description`)
- `CommandRegistry.canonical()` and `ToolRegistry.info()` accessors backing the `/help <name>` detail views
- `glob` tool — recursive pattern file discovery (`**/*.py`, `src/**/chat.py`); skips noise dirs (`.git`, `.venv`, `__pycache__`…), marks dirs with `/`, caps at 200 matches
- `grep` tool — regex content search returning `file:line: text` matches with an optional file-filter `glob`; skips noise dirs, caps at 100 matches, friendly invalid-regex error
- `/config` structured values — JSON auto-parse (`["run_command"]` → list, `0.3`/`2048`/`true` → number/bool), `-a`/`-r` list add/remove, `reload` re-reads config from disk (warns when provider/model changed), unknown keys prompt y/N before storing
- Command registration metadata — `description` and `subcommands` on `CommandRegistry.register()` (`self.meta`); canonical names tracked so aliases can't shadow real command names
- Machine access tools (`tools/machine.py`): `read_file` (numbered lines, `offset`/`limit`, truncation), `list_dir` (sorted entries, dir markers, sizes), `write_file` (parent-dir creation, write/append), `run_command` (subprocess exec with timeout, stdout/stderr capture, exit code, 8k output cap)
- Tool permission model (`tools/policy.py`) — `ToolPolicy` resolves each tool call to `allow`/`ask`/`deny` from configurable permission keys (`tool_permission`: `read`/`list`/`edit`/`bash`/`web`) plus name-level `tools.allow`/`tools.deny` (deny and allow-whitelist take precedence)
- Path-scoped confirmation — read/write/list calls targeting paths outside the project worktree escalate to `ask` (opencode-style `external_directory`), so in-worktree file ops run unattended while external access prompts
- Confirm prompts in the agent loop (`_confirm_tool`) — `bash: ask` by default so every `run_command` confirms; cancelled calls feed `[cancelled]` tool results back to the model; denied tools are filtered from the provider schema entirely
- Registration metadata — `category`, `permission`, `path_arg`, `key_arg` on `ToolRegistry.register()` plus `permission_for()`/`path_arg_for()`/`key_arg_for()`/`schema_filtered()`; retrofitted `web_search`/`fetch_page` (forward-compat for the deferred activity-lines glyph system)
- `tests/test_tool_policy.py` (allow/deny, permission keys, external-directory escalation, precedence) and `tests/test_machine_tools.py` (read/list/write/exec against a temp dir, timeout, metadata)
- `/tool` policy tests — deny rejection, `ask` accept/decline, schema filtering of denied tools
- `/help` `Available tools` section renders a clean two-column table using new `short=` registration labels (`Run a shell command`, `Search the web`, …); category/permission/action now show only in `/help <tool>` details
- `/help` is now the central help system — shows `Available commands` (aliases inline, subcommands at a standard 4-space indent) followed by `Available tools` (one per line with `[category · permission-key: action]`, policy-filtered)
- `/help <name>` shows details for a specific command (aliases + subcommands) or tool (`category`, `permission: action`, full parameter schema with required/optional); commands take precedence
- `/tool` (no args) lists allowed tool names one per line and points to `/help <tool>` for details
- `read_file` always emits a `# <path> — N lines` header (with the shown range when truncated) so the model knows the file's total size without extra reads
- `/help` compacts to one line per command with aliases inline (`/help, /h`) and subcommand rows beneath (`/session` → `new`/`list`/`load`/`delete`/`save`), all aligned to a computed description column
- `/session` (no args) reuses the shared subcommand metadata instead of a hardcoded usage block
- `/tool` command respects tool policy — listing shows only allowed tools, execution routes through `_run_tool()` (deny rejection + confirm prompts)
- `Session.to_dict()` and the agent loop unchanged — confirm prompts and tool status remain ephemeral REPL UI, never persisted
- `Config` shallow-copied `DEFAULT_CONFIG`, sharing the nested `tools.deny`/`tool_permission` lists/dicts across instances — mutations (e.g. `/config tools.deny -a …`) leaked into later sessions; now deep-copied on load and reload

## v0.6.0 - 2026-08-02

- `/tool <name> <json-args>` slash command — generic thin wrapper executing any registered tool via the same `ToolRegistry` the model uses; no args lists registered tools
- `tests/test_tool_registry.py` — registry metadata tests: `refine_required()` for `web_search` vs `fetch_page`/unknown
- `tests/test_commands.py` — `/tool` dispatch tests: registry execution, name listing, disabled path, invalid JSON
- Unified streaming agent loop (`_agent_loop()` in `chat.py`) — a single SSE stream per turn replaces the two-phase non-streaming decision + streaming call; `tool_calls` events are handled mid-stream, eliminating the double-call cost when no tools are used
- `_StreamRenderer` in `chat.py` — stateful streaming display (thinking markers, markdown, `<<<` prefix) extracted from the old `_stream_response` and reused across loop rounds
- `OllamaProvider.chat()` now accepts `tools`, forwards them in the stream payload, and accumulates fragmented `delta.tool_calls` into a `tool_calls` event
- `tests/helpers.py` — shared `make_chat()` builder for ChatLoop tests
- `tests/test_agent_loop.py` — loop-level tests: no-tools single round trip, thinking excluded from persisted content, error bail, empty stream
- `tests/test_ollama_provider.py` — provider streaming tests: fragmented tool-call accumulation, `done`/`thinking` events, `tools` in payload, error passthrough
- `ToolRegistry.register()` accepts `refine` metadata; `refine_required()` lookup added — `web_search` registered with `refine=True`, and `_execute_tool_calls()` now refines via metadata instead of special-casing the `web_search` name
- `BaseProvider.chat()` signature gains `tools: list[dict] | None = None`
- `_handle_message()` branches collapse onto `_agent_loop()`; `chat_nonstreaming()` is now used only by `_refine_query()`
- `tests/test_tool_calling.py` rewritten against the streaming event generator
- `_chat_with_tools()`, `_stream_response()`, `_output_content()` and `_response_start` from `chat.py`
- `/search` and `/web` slash commands — model tool-calling and `web_search` auto mode cover searching

## v0.5.0 — 2026-07-28

- `_TextExtractor` class in `tools/builtins.py` — stdlib HTMLParser-based text extraction for `fetch_page`
- Test `test_empty_stream_falls_back_to_nonstreaming_content` — verifies fallback saves non-streaming content when streaming returns empty
- `Session.to_dict()` filters out `role: tool` messages — session files only contain REPL-visible messages (user, assistant, command, system)
- Final assistant response missing from session when streaming returned no tokens — fall back to non-streaming result content when `_stream_response()` returns empty
- `fetch_page` returned raw HTML/JS/CSS noise — replaced regex tag-stripping with `_TextExtractor` (HTMLParser) that drops `<script>`, `<style>`, `<svg>`, `<noscript>` and extracts clean visible text
- Session files stored raw tool-result content that was never displayed in the REPL — filtered `role: tool` messages from serialized output; assistant `tool_calls` (web_search, fetch_page declarations) still documented

## v0.4.0 — 2026-07-28

- 3 new test cases: empty-content, multiple tool calls, and API error path (now 7 tests total)
- Tool-call messages (assistant tool_calls + tool results) lost when streaming produced empty content or an exception occurred — wrapped `_chat_with_tools()` and `_stream_response()` in `try/finally` so session is always persisted
- `_chat_with_tools()` no longer skips `_stream_response()` when `chat_nonstreaming` returns empty/null content — final response is always streamed
- Session file rename left JSON `name` field stale — added `session_auto_save()` after rename so the file always has the correct session name

## v0.3.0 — 2026-07-28

- Auto-session naming: first user message auto-names the session (sanitized, truncated to 40 chars). Renames the `.json` file on disk
- Markdown-aware streaming: code blocks in cyan, inline code in green, bold text rendered with ANSI bold. Disabled by default (`markdown_streaming: false`). Enable via config.
- Thinking/reasoning token detection: provider-level `reasoning_content` field (DeepSeek R1, o1, o3). Configurable via `show_thinking` (default `true`)
- Error handling: `_post()`, `chat_nonstreaming()`, `chat()`, `_chat_with_tools()`, and `list_models()` now catch `HTTPError` (auth 401, server 500) and `URLError` (network, timeout) gracefully — errors print in red, REPL continues
- `_chat_with_tools()`: when no tools are used, now calls `_stream_response()` for live token output instead of dumping the full response at once
- `query_refine` config system: when enabled, short web_search queries (≤ `query_refine_min_words` words) are auto-refined via a lightweight model call with `query_refine_context` recent messages as context. Configurable via `query_refine`, `query_refine_min_words` (default 3), `query_refine_context` (default 4)
- `tool_status_visible` config option (default `true`): when `false`, hides dimmed `[tool: args]` status lines during tool execution
- Mock test suite for tool calling (`tests/test_tool_calling.py`): 4 offline tests covering no-tools, single-tool, unknown-tool error, and force-search paths
- Markdown streaming now off by default; the state machine was unreliable on real streaming output
- Removed `...` as thinking marker/closer (too many false positives in normal text)

## v0.2.0 — 2026-07-27

- Auto-search mode: set `web_search: true` in config to search on every message
- Search results displayed as compact list, injected as AI context for grounded responses
- `/search <query>` and `/web <query>` commands
- `web/display.py` — `format_results()` for terminal, `format_context()` for AI context injection
- `web/search.py` — `DDGResultParser` (HTMLParser), search endpoint at `lite.duckduckgo.com`
- Web search: DuckDuckGo Lite via `html.parser` — `/search <query>` and `/web <query>` commands
- Config default: `tool_calling: true`
- `/search` command integrated with tool calling (uses `_chat_with_tools(force_search=...)`)
- `_show_tool_status()` — dimmed `[web_search: "query"]` status during tool execution
- `_chat_with_tools()` — decision loop that executes tool calls and injects results
- Ollama provider: refactored payload generation, `chat_nonstreaming()` with `tools` support
- `BaseProvider.chat_nonstreaming()` — returns `{role, content, tool_calls, finish_reason}`
- `tools/builtins.py` — `web_search` and `fetch_page` tools
- `tools/registry.py` — decorator-based tool registration (OpenAI function calling format)
- Tool calling system: two-phase chat (non-streaming tool decision → stream final content)

## v0.1.0 — 2026-07-27

- `<<< ` prefix on streaming responses for clear user/AI separation
- Command logging: all slash commands stored as `command`-role messages in session history
- Model tracking: per-message `model` + `provider` on each assistant response
- Elapsed time display after each response
- Timestamps on every message and duration tracking on assistant responses
- Streaming token display with ANSI-colored prompt
- REPL loop with readline input history and tab completion
- Built-in slash commands: `/help`, `/connect`, `/model`, `/provider`, `/session`, `/config`, `/exit`
- Command registry with decorator-based registration
- Session manager: create, list, load, delete, auto-save (JSON format)
- Ollama cloud provider (defaults to `https://api.ollama.com`)
- Provider abstraction layer (OpenAI-compatible `/v1/chat/completions`)
- HTTP SSE streaming via urllib for live token output
- Config module: global + local JSON merge (`~/.config/replio/` + `.replio/`)
- Project scaffold (pyproject.toml, .venv, directory structure)
