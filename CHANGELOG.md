# Changelog

## v0.18.0

- Word-level streaming buffering - the REPL now buffers streamed tokens to word boundaries and prints whole words as they complete, so responses render smoothly without mid-word pauses or breaks. The `<<< ` prefix appears on the first printed word, indentation and newlines flush correctly, and the trailing partial word is written before any status line, confirm prompt, or the turn footer. `HeadlessUI` and `NullUI` stream unchanged, and the content persisted to sessions is untouched. Gated by the new `word_streaming` config (default `true`), off restores character-by-character streaming
- Multi-line REPL input - opening `"""` or `'''` switches the prompt to `...` until the block closes. The composed prompt is sent as one turn with the framing quotes stripped (both `"""..."""` and `task: """..."""` work, indentation inside the block is kept, and the block is a single history entry). Balancing is overlap-aware, so `""""` reads as a matched pair. Ctrl-C or EOF on an open block exits the REPL cleanly instead of swallowing the interrupt
- Available models are now discoverable - `/models` (alias `/model-list`) lists the connected provider's models. `replio models [--path]` does the same headlessly and exits `1` on a failed probe. When `/connect` saves a config whose model is missing from the advertised list, it offers `Show available models? [y/N]`. `Engine.check_connection()` now returns `(ok, message, models)` from a single `_fetch_models()` call, and `Engine.list_models()` proxies the same shared fetch. `list_models()` dropped its inline `[Error]` print (pure, returns `[]` on failure)
- Multi-line input tests - `tests/test_repl_input.py` (22 tests: overlap-aware open-delim detection, framing strip variants incl. indentation and `'''`, and run-loop flows for single-line, block composition, EOF exit inside a block, and untouched slash commands)
- Word-streaming tests - `tests/test_ui.py` (9 tests: boundary and tail flush, multi-word chunks hold only the partial word, newline flush, footer flush with separator newline, off-mode immediate writes, markdown bold across a flush boundary, flush before status and confirm prompts)
- `/connect` tests the provider connection before saving - a `GET <base_url>/v1/models` probe via `OpenAICompatibleProvider.check_connection()` over the shared `_fetch_models()` helper. Broken values print the error and need an explicit `Save anyway? [y/N]` to persist. A success message notes when the configured model is missing from the model list
- `/provider <name>` switches then probes the new connection and prints a warning when it fails (`Run /connect to fix`). Both probes are gated by the new `connect_check` config (default `true`). Set it to `false` to skip them for offline or flaky networks
- `Engine.check_connection()` probes a throwaway provider built from optional overrides (never mutates `config`/`self.provider`), with provider resolution extracted into `_resolve_provider_factory()` (also cleans up `_reinit_provider`'s unknown-provider handling)
- Tests - `check_connection` and `list_models` coverage in `tests/test_providers.py` (loopback success/empty/model-note/HTTP, network error, silent-on-error) and `tests/test_engine.py` (resolution, override precedence, no state mutation, base-URL detection, `list_models`). `/connect` probe-before-commit (decline keeps config, accept saves, `connect_check: false` skips, model-mismatch show offer) plus `/models` and `/provider` warn in `tests/test_commands.py`. `replio models` in `tests/test_cli.py`. Docs in `docs/config.md` (`connect_check`), `docs/providers.md`, `docs/commands.md`, `docs/testing.md`
- `replio export <name> [--out <file>]` - headless Markdown export for scripts and CI, reusing the same renderer and defaulting to the same `.replio/exports/<name>.md` target (`--out -` prints to stdout, exit `1` on an unknown session)
- Session export to Markdown - `/session export <name> [out]` renders any saved session as a Markdown transcript (default `.replio/exports/<name>.md`, custom path via the second arg, `-` for stdout). The pure renderer in `sessions/render.py` covers the full persisted log: thinking, tool calls and results as fenced code blocks, tool `analysis`, `command` records, compaction summaries with the trimmed boundary, and the `## Errors` section. It reads via `read()` (never switches the current session) and carries serialization-time transforms (`noise_tools`, `session_tool_max_chars`) through as persisted
- `/session export` completes session names in the REPL, and the export format is documented in `docs/session.md`
- Tests - `tests/test_session_render.py` (17 tests: renderer output per role, fence escaping for backtick-heavy tool results, persisted noise transforms, and `/session export` dispatch covering default/custom/stdout targets and the non-destructive read) plus `tests/test_cli.py` for `replio export` (default/custom/stdout targets, unknown session, `main` dispatch)

## v0.17.0 - 2026-08-21

- Failed tool calls now render a dimmed `! Error: ...` line (first line of the result) under the activity line, for every tool through the shared dispatch point (agent loop, `/tool`, policy-denied calls), gated by the new `show_errors` config (default `true`)
- `list_dir` and `grep` get the `*` glyph with distinct verbs (`* List`, `* Grep`), matching `glob`'s `* Glob` - they no longer render as `← Read`, which made directory listings and greps look like `read_file` calls
- `run_command` now validates `cwd` (friendly `Error: cwd not found` instead of an `OSError`) and clamps `timeout` to 1..600 seconds, so a nonsense value like `10000` no longer executes
- The confirm prompt prefix changed from `↳` to `?` so it no longer collides with the reserved delegate-category glyph
- Glyph activity lines and confirm prompts now show the parameters the model passed (`← Read engine.py [offset=299, limit=85]`, `$ Run pytest [cwd=/workspace, timeout=600]`), gated by the new `glyph_params` config (default `true`). The label's own argument is not repeated
- `max_tokens` now defaults to `8192` (sent to the provider, overriding low provider-side defaults like Ollama's 2048 cap). Setting it to `0` omits it from the payload so the provider's own default applies
- Truncation messages now distinguish a configured `max_tokens` cap from the provider's own default limit (no more misleading `(0)` in the session log when the limit is unset)
- Session auto-names are now ASCII-only: non-ASCII letters are transliterated (NFKD, e.g. `prüfe` becomes `prufe`) instead of being stored in filenames
- `/help` now lists tools as indented subcommand-style rows under `/tool` (replacing the separate "Available tools:" section), filtered by policy and mode like the `/tool` listing. Bare `/tool` shows the same rows with short descriptions
- Fixed streaming and non-streaming provider requests failing with `405 Method Not Allowed` on endpoints that redirect - urllib converts POST to GET on 301/302/303 redirects, so `api.ollama.com/v1/chat/completions` (which 301-redirects to `ollama.com`) ended up GETting the chat endpoint and getting 405 back. A `PostRedirectHandler` now preserves the POST method and body across redirects (`utils/http.py`, `providers/base.py`), with loopback-server tests for both the SSE stream and non-streaming `_post`
- Fixed OpenAI/Groq/Anthropic provider defaults posting to a doubled path - `DEFAULT_BASE_URL` already includes `/v1`, and `_endpoint()` appended `/v1/chat/completions` again, producing `/v1/v1/chat/completions` (404). `_endpoint()` and `list_models()` now normalize a trailing `/v1` instead of doubling it, so default and custom base URLs both resolve correctly
- Plan/Build (and custom) agent modes - a mode is a named posture combining a system instruction with tool-policy overrides. New `mode` (default `build`) and `modes` config keys ship the built-ins: `build` (no overrides, current behavior) and `plan` (read-only - denies the `edit` and `bash` categories and instructs the model to investigate and propose rather than modify). Custom modes can set `system_prompt`, `tool_permission` (merged over the base, mode wins per key), `tools.deny` (appended), and `tools.allow` (replaces when non-empty). An unknown `mode` falls back to `build` with no error
- `/mode` command - no args lists the current mode and all defined modes, `/mode <name>` switches live (the next turn uses the new posture, mode switches are recorded as `command` messages), unknown names print the valid list. Mode names tab-complete in the REPL. The REPL banner and the `replio serve` stderr line show the active mode when it is not `build`
- `--mode <name>` CLI flag on `replio run` and `replio serve` - headless agents start in the given posture (e.g. `replio run --mode plan` for a read-only review run)
- Mode mechanics reuse the existing `ToolPolicy` - no new machinery: `ToolPolicy.allowed()` is now permission-aware, so a category-level `deny` (`tool_permission.edit: deny` and `tool_permission.bash: deny`) filters the tool from the provider schema and from `/tool`/`/help` listings, not just direct calls. The MCP server's tool listing honors the same filtering
- Mode instructions and `system_prompt` are injected at the engine level (`_provider_messages`) as a virtual system message, so the REPL, `replio run`, `replio serve`, and MCP all apply them. Headless modes now receive `system_prompt` (previously REPL-only, persisted as a session message - that block is removed)
- Sessions record the active mode on every assistant message (`mode` field, parity with `reasoning`), so the posture in effect per turn is auditable from the append-only log
- Tests - `tests/test_modes.py` (12 tests: resolve/merge rules, unknown fallback, instruction composition), plus plan-mode schema filtering, instruction injection, per-message mode, `/mode` command and completer, `--mode` CLI, and permission-aware `allowed()` coverage in engine/commands/cli/policy tests
- Docs - `docs/config.md` (mode/modes schema + semantics), `docs/commands.md` (`/mode`, `--mode`), `docs/tools.md` (category-deny schema filtering, mode layering), `docs/security.md` (Modes section), `docs/session.md` (`mode` field), README feature line, developer use-case guide updated

## v0.16.0 - 2026-08-20

- Reasoning persisted in session logs - each `assistant` message records the `reasoning` config value in effect, alongside the existing `thinking` text. Reasoning text is always logged regardless of `show_thinking` (display hides it but never drops it from the log)
- Thinking/reasoning toggle - two orthogonal knobs: `show_thinking` (default `false`) controls display (stream reasoning dimmed when on, else an animated spinner + `+ Thought N.Ns` summary), and `reasoning` (default `"auto"`) requests reasoning from the model and controls its token budget. `reasoning` maps `false`/`"off"` (no request), `true`/`"on"`/`"auto"` (provider default), and `"low"`/`"medium"`/`"high"` (budget hint) to provider params - OpenAI `reasoning_effort`, Anthropic `thinking.budget_tokens` (1024/2048/4096), Qwen/Ollama `enable_thinking` - with a generic `reasoning_effort` pass-through for other OpenAI-compatible endpoints. The `/thinking on|off|?` command toggles `show_thinking` live
- Thinking spinner - when `show_thinking: false` the REPL now shows an animated `⠋⠙⠹...` spinner (stdlib `threading` daemon, `\r\033[K` cleared) in place of the silent wait, then falls back to the `+ Thought N.Ns` summary. No new config key - folded into `show_thinking`. Interactive `ReplUI` only, headless stderr output unchanged
- Activity lines and tool status are ephemeral UI - emitted through the UI sink only and never persisted to session files (tool calls/results are recorded there). Regression test locks this in

## v0.15.0 - 2026-08-18

- MCP (Model Context Protocol) support via the bundled `replio-core-mcp` plugin (stdlib-only - JSON-RPC 2.0 over newline-delimited stdio and SSE over urllib, no third-party `mcp` library)
- MCP client - connect to external servers over stdio or streamable HTTP and import their tools into the ToolRegistry, named `<prefix>.<tool>` and registered under the new `mcp` permission category (default `ask`, so each remote call confirms in the REPL). Management tools `mcp_connect`/`mcp_list`/`mcp_disconnect` and a `/mcp` command wrap the same registry dispatch. `mcp.servers` config defines server name, transport, command/url, prefix, headers, and timeout
- Dual-era negotiation - the client probes `server/discover` (modern 2026-07-28 per-request `_meta` protocol) and falls back to the legacy `initialize` handshake (2025-11-25 and earlier), accepting a mutually supported version on unsupported-version errors
- MCP server - exposes Replio's policy-filtered tools and its sessions as resources (`replio://session/<name>`) to external agents, over stdio (`replio mcp`) and HTTP (`POST /mcp` on `replio serve`). The server is dual-era too, serving `server/discover`/modern requests or the legacy `initialize` handshake depending on how the client opens. `ask`-policy tools run by default when serving (`mcp_server.allow_ask`, deferred to the external client as the human-in-the-loop)
- Core stays MCP-agnostic - `replio mcp` and the `/mcp` HTTP route delegate to the plugin's `mcp_server` service (same generic `register_services` pattern as the web-search service), erroring cleanly if the plugin is not loaded
- Tests - `tests/test_mcp.py` (27 tests): JSON-RPC framing, stdio/HTTP transports over real subprocesses and a loopback server, modern/legacy negotiation, tool import + prefixing, server dispatch (initialize/discover/tools/call/resources), `_meta` validation, and policy integration
- Docs - `docs/mcp.md` (config schema, client + server usage, interop note and security), bundled-plugin and config/tools/testing references updated

## v0.14.0 - 2026-08-17

- Alias layer for tools and params - tool names can register `aliases` (`read`/`view` > read_file, `ls` > list_dir, `bash`/`exec` > run_command) and `param_aliases` (`file` > path, `query` > pattern, `cmd` > command, `q` > query, `cursor` > offset). The registry resolves aliases to the canonical tool and normalizes args, so the advertised schema stays in the project's own vocabulary while model-dialect tool and argument names are absorbed. `/tool`, `/help`, tool policy, confirm prompts, and glyph activity lines work through aliases unchanged
- `open` web tool (replio-core-websearch) - fetch a web page by `id` (1-based result from the most recent `web_search`) or `url`, with `offset` (also accepted as `cursor`) to resume reading. `web_search` now retains its last results for `open` to resolve, and a shared `_fetch_text` helper gives both `fetch_page` and `open` offset-with-continuation paging, appending `[offset N of M chars - continue with cursor=N]` when content continues past the cap
- Configurable stream retry - a provider stream that ends before a completion event with no streamed content is re-requested up to `1 + stream_retries` times (default 3 total attempts, configurable) with `stream_retry_delay` (default 0.5s) between attempts. The retrying note shows the attempt count, and when tool calls have already run the warning notes the results are saved so the answer can be retried with a follow-up message
- `tool_max_result_chars` config (default `0` = unlimited) - replaces the bundled plugins' hardcoded 8000-char tool-result cap with a configurable one (set via `/config tool_max_result_chars N`). With the default nothing is truncated, `read_file` headers now report the total line and character count so the model can page large files with `offset`/`limit`, and `read_file(path, limit=0)` returns just the header as a size probe before committing to a read. Handlers can read the config via a `_config` kwarg the registry passes only when declared
- Glyph activity lines - typed `<glyph> <verb> <key_arg>` status (dimmed) replaces the `[tool: key_arg]` oneliner for mapped categories, gated by the new `glyph_lines` config (default `true`). `ToolRegistry.activity()` resolves the glyph from category defaults (read `←` Read, write `→` Write, search `%` Search, exec `$` Run, ask `~` Ask, todo `-` Todo, delegate `↳` Call) or per-tool `glyph`/`verb` overrides (glob `*` Glob, fetch_page `↓` Fetch). Disabling `glyph_lines` or an unmapped category keeps the `[tool: key_arg]` oneliner + detail lines. `ReplUI`/`HeadlessUI` render the glyph line, ephemeral UI only (never persisted to session files)
- `write_file` reports the resolved absolute path to the model - the tool result now returns `Created|Overwritten|Appended <resolved abs path> (<n> lines, <n> chars)` instead of echoing the raw `path` arg, so when a relative path resolves to an unexpected directory (e.g. launched from `~`) the model sees where the file actually landed, the tool description notes that relative paths resolve against the current working directory. Terminal status preview unchanged. Tests: create/overwrite/append result strings and relative-path resolution
- Tab completion extended - filesystem path completion after command arguments (directories get a trailing `/` for continued descent), tool-name completion for `/tool <prefix>`, and subcommand completion for commands declaring `subcommands` (`/session lo` > `load`, `/plugins dis` > `disable`)
- Fixed tab completion - the completer no longer fires on macOS libedit (`readline.parse_and_bind('tab: complete')` is GNU-only and silently inserts a literal tab, libedit needs `bind ^I rl_complete`). `/` is removed from the completer delimiters so the model-facing word keeps its slash and paths complete correctly

## v0.13.0 - 2026-08-16

- Per-turn stats on their own line - the `(Ns, N tokens)` footer no longer lands at the end of the last content line, `ReplUI` tracks whether streamed output ended with a newline and emits a separating one before the footer
- One-shot retry for empty/truncated streams - a provider stream that ends without a completion event and with no streamed content is requested once more (with a "retrying" note) before the "Stream ended before a completion event" error is surfaced, masks transient provider drops such as Ollama cloud returning an empty follow-up stream after a tool call
- `write_file` status preview ends with a dimmed parenthesized summary - resolved absolute path, line count, char count, and created/overwritten/appended action (tool result string stays minimal)
- Thinking announce - `+ Thinking` on its own line before streamed reasoning when `show_thinking: true`, when hidden, `+ Thought 12.3s` (thinking duration) is printed instead and the reasoning text stays out of the terminal. The engine times the thinking window (`thinking_begin`/`thinking_end` UI hooks), `HeadlessUI` mirrors it in `--verbose` mode, and a spinner (`⠧ Thinking`) can replace the static markers later
- Human-readable tool status - default oneliner is now `[tool: key_arg]` (e.g. `[write_file: test.md]`, `[run_command: echo hi]`) instead of the raw args dump (`content='...\n...', mode='w'`), detail lines follow dimmed: `write_file` shows the written text via a registered `status` callback (new-file `+ line` preview, or a `difflib` unified diff of existing files - works for append too), and `run_command` echoes its output (`echo` registration metadata)
- `list_dir` gains `depth` (default 1) - higher values render an indented recursive tree (`tree -L` style), skipping `SKIP_DIRS` during descent, `depth=1` output is unchanged
- `ToolRegistry.execute()` drops arguments not declared in a tool's schema and `null`-valued arguments (e.g. a hallucinated `recursive`, or `depth: null`) - tools run with their valid args instead of erroring, worktree semantics documented (worktree = launch directory / `--path`, launching from `~` makes home the worktree, so subdirectories don't escalate)
- **Built-in features ship as bundled plugins** - `web_search`/`fetch_page` and the machine tools (read_file, list_dir, write_file, glob, grep, run_command) moved out of the core (`src/replio/web/`, `tools/builtins.py`, `tools/machine.py` deleted) into three first-party bundled plugins under `plugins/` (shipped as `replio.plugins.bundled`): `replio-core-websearch`, `replio-core-fs`, `replio-core-exec`. Packaged via `package-dir` mapping, so the repo-root `plugins/` directory is the canonical source, discovery adds a bundled root with precedence bundled < global < local (local/global overrides win)
- **`plugins` config list** - replaces `plugins.enabled`/`plugins.deny` (migrated automatically). The default config lists the bundled plugins so they are active out of the box, empty list = all discovered plugins load, `/plugins enable/disable` and `install`/`uninstall` maintain the list
- **`register_services` entry hook** - plugins can power core non-tool features. `replio-core-websearch` registers the `search` service backing the `web_search: true` search-then-answer mode (`engine._perform_search` now routes through it and degrades gracefully when the plugin is absent)
- `PluginInfo.origin` (`bundled`/`global`/`local`) shown in `/plugins` and `replio plugins list`, bundled plugins cannot be `update`d or `uninstall`ed (disable instead)
- `tests/test_bundled_plugins.py` (10 tests) - bundled discovery, tool registration, search service, bundled uninstall/update blocking, local override, config disable, default-config membership, `test_tool_registry.py`/`test_machine_tools.py`/`test_commands.py`/`test_tool_calling.py`/`test_session_log.py` reworked to load bundled plugins and patch the search service instead of `replio.web.search`

## v0.12.0 - 2026-08-15

- Plugin system (`src/replio/plugins/`) - external repositories register **tools, providers, and slash commands** without changing the core, `PluginManager` discovers plugins in `~/.config/replio/plugins/` and `.replio/plugins/` (local wins), validates `manifest.json` (`replio_version`/`python` semver ranges), imports entry modules once, and hooks them into the live registries
- Plugin entry contract - optional `register_tools(registry)` / `register_providers(providers)` / `register_commands(commands)` hooks on the entry module, matching the core's `register_*` conventions, plugin tools automatically inherit tool policy, `/tool`, `/help`, refinement, and session logging
- Lazy plugin dependencies - third-party packages are imported inside plugin functions (never by the core), so the stdlib-only guarantee holds and a missing dep surfaces as a tool error with `pip install` guidance
- `/plugins` command (`/plugins list`, `/plugins <name>` detail with per-dep status, `enable`/`disable`, `install`/`update`/`uninstall`) plus tab completion for plugin names, `/connect` now offers plugin providers
- `replio plugins` CLI (`list`/`install`/`update`/`uninstall`) - headless plugin management so `replio run`/CI can use freshly installed plugins, `install` clones a git URL or copies a local path, records `source`, and `--deps` pip-installs the declared `requires`
- Config keys `plugins.enabled` (allowlist, empty = all) and `plugins.deny` (always excluded) - activation is explicit and applies on the next start
- `docs/plugins.md` - plugin layout, manifest schema, compatibility contract, entry hooks, management, security, and future paths (per-plugin venv isolation, PyPI entry-point source, migrating core web tools out)
- `tests/test_plugins.py` (30 tests) - manifest parsing, `replio_version`/`python` compat skipping, enable/deny filtering, global/local precedence, entry load-error isolation, all three registration hooks, lazy-dep pip guidance, tool-policy filtering, install/update/uninstall from a local path, and Engine integration (tools + commands + `/plugins`)
- REPL banner shows the version - `Replio v0.12.0 (provider: model)` on startup, gated by `show_version` config (default `true`), toggleable via `/config show_version false`
- `GET /version` endpoint - the serve API exposes the installed version as `{"version": ...}`, alongside `/health` and `/sessions`
- `/version` slash command (alias `/v`) - prints `Replio <version>` in the REPL, version lookup centralized in `replio.get_version()` and shared with the CLI `--version` flag
- `--version` / `-v` CLI flag - `replio --version` prints the installed version (from package metadata) and exits
- Clear screen on REPL start - the interactive REPL wipes scrollback + visible screen (`\033[3J\033[2J\033[H`) before printing the banner, gated by `clear_screen` config (default `true`), toggleable via `/config clear_screen false`. Headless `run`/`serve` modes are unaffected.

## v0.11.0 - 2026-08-14

- `Engine` headless agent core (`engine.py`) + `TurnResult` - the agent loop extracted from `ChatLoop` returns a structured `{content, thinking, tool_calls, errors, duration, usage, model, provider, session, status}` turn result, `Engine.chat(text, autoname=True)` and `Engine.load_or_create_session(name)` make sessions addressable from any front-end
- `UISink` abstraction (`ui.py`) - the loop renders through `ReplUI` (terminal ANSI streaming, confirm prompts, footer), `HeadlessUI` (stderr diagnostics, auto-approve/deny confirm policy, never blocks on stdin), or `NullUI` (silent)
- `replio run` - one-shot CLI mode (JSON or text output) over the same agent loop + session manager, flags `--prompt`, `--provider`, `--model`, `--base-url`, `--output`, `--verbose`, `--session-id`, `--yes`/`--no`, exits `0` on ok/truncated and `1` on error/empty
- `replio serve` - stdlib `ThreadingHTTPServer` JSON API (`POST /chat`, `GET /sessions`, `GET /health`) with a shared engine serialized behind a lock, ask-gated tools are denied (fed back as `[cancelled]`), the server never blocks on stdin
- Headless `ask` policy - tools gated by `ask` are denied by default in headless mode, `--yes`/`--no` override to approve or deny
- Tests for headless entry points - `test_engine.py` (turn result, thinking split, session addressing, confirm policy), `test_cli.py` (mock provider, JSON/text output, session-id persistence, exit codes), `test_server.py` (ephemeral-port server against a mocked provider)
- `ChatLoop` is now `ChatLoop(Engine)` - a thin REPL shell (readline, banner, prompt loop) inheriting the headless core, commands and session logic are unchanged
- `_handle_message()` replaced by `Engine.chat()`, `_StreamRenderer` moved into `ReplUI`, and the `<thinking>` marker split is owned by the engine so thinking stays separate from content in JSON results
- The `input()` confirm prompt moved from `chat.py` to `ui.py` (tests patch `replio.ui.input`)

## v0.10.0 - 2026-08-13

- OpenAI, Groq, and Anthropic providers (`providers/openai.py`, `providers/groq.py`, `providers/anthropic.py`) - OpenAI-compatible `/v1/chat/completions` subclasses of the shared `OpenAICompatibleProvider`, each with its own default `base_url` and default model (`gpt-4o-mini`, `llama-3.3-70b-versatile`, `claude-sonnet-4-20250514`)
- Provider auto-detection - `detect_provider(base_url)` in `providers/__init__.py` matches well-known hosts (`openai.com`, `groq.com`, `anthropic.com`, `ollama.com`/`ollama.ai`) and falls back to the generic `openai-compatible` provider for any other OpenAI-compatible endpoint
- `PROVIDERS` registry - `_reinit_provider()` resolves the configured provider name through the dict (`ollama`, `openai`, `groq`, `anthropic`, `openai-compatible`), unknown names are auto-detected from `base_url` with a printed note instead of silently falling back to ollama
- `/connect` detects the provider from the entered base URL and switches automatically when it matches a known host
- Agent-loop hardening - streamed content is persisted when the SSE stream ends without a `done` event, and session `errors` entries are recorded for silent failures: stream EOF before a completion event, empty/thinking-only `done`, and unexpected exceptions escaping the agent loop, unexpected exceptions in `run()` are caught, logged to the session `errors`, and the REPL stays alive instead of crashing
- `tests/test_providers.py` - provider defaults, auth header, `detect_provider`, and registry coverage
- `OllamaProvider` now subclasses the shared `OpenAICompatibleProvider` - the streaming/tool-call/error logic it previously owned moved to `providers/base.py`, behavior unchanged
- Switching providers swaps in the new provider's default `base_url`/`model` when the configured values still match another provider's default (i.e. were never customized), explicit custom values are preserved
- `tests/test_ollama_provider.py` - `stream_sse` patches retargeted to the base module where the streaming logic now lives

## v0.9.0 - 2026-08-12

- `/session preview <name>` - read-only structural preview (name, created/updated, message counts by role, tools used) without switching the active session, shown on `/session load` too
- `noise_tools` config (default `["fetch_page"]`) - results of these tools are replaced by a `[<tool> result excluded from log, see tool call above for parameters]` marker at persistence time only, the live turn still feeds the full result to the model, and the assistant `tool_calls` message keeps the query/URL so the log stays reproducible
- Session-name tab completion - `/session load` and `/session delete` complete against saved session names (bash-style common-prefix completion, double-tab lists candidates)
- Compaction summary visibility - `/compact` and `/session load` (when the compaction offer is accepted) print the generated summary text, stored as the `result` of the triggering `command` message (with a `compact_from` boundary index)
- Context-size visibility - dimmed `(Ns, N tokens)` line after each response, using the provider's `usage.prompt_tokens` when reported (fallback: char-based estimate), gated by `show_context_size` (default `true`)
- `/session load` compaction offer - always prompts `Summarize & trim history before continuing? [y/N]`
- `tests/test_http.py` - `stream_sse` survives a multi-byte UTF-8 character split across 4096-byte read chunks, normal data-line flow, and `[DONE]`/error passthrough
- Sessions are **append-only logs** - compaction no longer removes or rewrites session entries, it only trims the provider context via the summary record and boundary, so the full history always stays in the file
- Provider payload is prepared from the log - `role: command` messages are never sent as-is, compaction summary records convert to `system` messages, and dangling tool messages are skipped
- `/session load` and `/session preview` print a structural preview, `/session load` records the load as a `command` message in the loaded session
- `max_tokens` default is now `0` (unset) - the value is omitted from the provider payload entirely, so the provider's own default applies and long answers are no longer cut at the old 2048-token default, set a cap explicitly via `/config max_tokens N`
- `/session new` and `/session load` now reassign `ChatLoop.current_session` - previously they only updated `SessionManager.current`, so loaded/new sessions were never actually used for prompts, rendering, or autosave
- If a configured `max_tokens` cap is hit (`finish_reason: length`), the loop now prints a visible truncation warning and records a session `errors` entry instead of stopping silently
- `OllamaProvider.chat()` streaming captures `usage` from the final chunk and attaches it to the `done` event
- `config.py` - new keys `show_context_size`, `compact_keep` (default `4`), `noise_tools` (default `["fetch_page"]`), removed `compact_prompt_chars`
- Compaction failed with sessions containing `command`/tool messages - the summarizer now sanitizes the batch (drops `command`, drops `tool_calls` declarations, converts `tool` > `user [tool result]`), and provider errors are printed instead of swallowed as a generic "Compaction failed"
- Tab completion for `/` commands never matched - readline passes the current word, and command names have no leading slash, so the prefix test always failed, the completer now strips the `/` when comparing and re-adds it on completion
- `stream_sse` decoded each 4096-byte chunk with strict UTF-8, so a multi-byte character split across a chunk boundary raised `UnicodeDecodeError` - caught as a generic error that aborted the stream mid-output and killed the tool loop during long web research, buffering is now byte-based and each complete line is decoded with `errors='replace'`

## v0.8.0 - 2026-08-05

- `Session` metadata - `created_at`/`updated_at` (bumped on every message) and a top-level `errors` array with `add_error()`, `to_dict()` now persists **every** message, including `role: tool`
- `tool_analysis` config (default `false`) - optional model-generated one-line insight summary stored as `analysis` on each tool message, so a session log can be reconstructed without re-running the tool, skipped for `[cancelled]`/error results
- `session_tool_max_chars` config (default `0` = unlimited) - caps persisted tool-result content at serialization time only, the in-memory provider context always keeps full results
- `_StreamRenderer` captures `thinking_text`, `_agent_loop` persists per-round reasoning as `thinking` metadata on tool-call and final assistant messages (still excluded from `content`)
- Provider `error` events now append to the session `errors` array before the loop bails, instead of being dropped
- `tests/test_session_log.py` - session model, save/load round-trip, legacy-file loading, `tool_max_chars` truncation, thinking metadata, and `tool_analysis` behavior
- `SessionManager.save()` accepts `tool_max_chars`, `session_auto_save()` forwards the config value
- `_execute_tool_calls()` appends assistant tool-call and tool-result messages via `Session.add_message()` (single timestamp/`updated_at` path instead of direct list appends)
- Docs updated to match: session files are now complete logs (tool results, thinking, errors), confirm prompts and tool status remain ephemeral UI

## v0.7.0 - 2026-08-03

- Tool `short=` registration metadata - human-readable one-line labels for the `/help` tools table (falls back to a truncated `description`)
- `CommandRegistry.canonical()` and `ToolRegistry.info()` accessors backing the `/help <name>` detail views
- `glob` tool - recursive pattern file discovery (`**/*.py`, `src/**/chat.py`), skips noise dirs (`.git`, `.venv`, `__pycache__`...), marks dirs with `/`, caps at 200 matches
- `grep` tool - regex content search returning `file:line: text` matches with an optional file-filter `glob`, skips noise dirs, caps at 100 matches, friendly invalid-regex error
- `/config` structured values - JSON auto-parse (`["run_command"]` > list, `0.3`/`2048`/`true` > number/bool), `-a`/`-r` list add/remove, `reload` re-reads config from disk (warns when provider/model changed), unknown keys prompt y/N before storing
- Command registration metadata - `description` and `subcommands` on `CommandRegistry.register()` (`self.meta`), canonical names tracked so aliases can't shadow real command names
- Machine access tools (`tools/machine.py`): `read_file` (numbered lines, `offset`/`limit`, truncation), `list_dir` (sorted entries, dir markers, sizes), `write_file` (parent-dir creation, write/append), `run_command` (subprocess exec with timeout, stdout/stderr capture, exit code, 8k output cap)
- Tool permission model (`tools/policy.py`) - `ToolPolicy` resolves each tool call to `allow`/`ask`/`deny` from configurable permission keys (`tool_permission`: `read`/`list`/`edit`/`bash`/`web`) plus name-level `tools.allow`/`tools.deny` (deny and allow-whitelist take precedence)
- Path-scoped confirmation - read/write/list calls targeting paths outside the project worktree escalate to `ask` (opencode-style `external_directory`), so in-worktree file ops run unattended while external access prompts
- Confirm prompts in the agent loop (`_confirm_tool`) - `bash: ask` by default so every `run_command` confirms, cancelled calls feed `[cancelled]` tool results back to the model, denied tools are filtered from the provider schema entirely
- Registration metadata - `category`, `permission`, `path_arg`, `key_arg` on `ToolRegistry.register()` plus `permission_for()`/`path_arg_for()`/`key_arg_for()`/`schema_filtered()`, retrofitted `web_search`/`fetch_page` (forward-compat for the deferred activity-lines glyph system)
- `tests/test_tool_policy.py` (allow/deny, permission keys, external-directory escalation, precedence) and `tests/test_machine_tools.py` (read/list/write/exec against a temp dir, timeout, metadata)
- `/tool` policy tests - deny rejection, `ask` accept/decline, schema filtering of denied tools
- `/help` `Available tools` section renders a clean two-column table using new `short=` registration labels (`Run a shell command`, `Search the web`, ...), category/permission/action now show only in `/help <tool>` details
- `/help` is now the central help system - shows `Available commands` (aliases inline, subcommands at a standard 4-space indent) followed by `Available tools` (one per line with `[category · permission-key: action]`, policy-filtered)
- `/help <name>` shows details for a specific command (aliases + subcommands) or tool (`category`, `permission: action`, full parameter schema with required/optional), commands take precedence
- `/tool` (no args) lists allowed tool names one per line and points to `/help <tool>` for details
- `read_file` always emits a `# <path> - N lines` header (with the shown range when truncated) so the model knows the file's total size without extra reads
- `/help` compacts to one line per command with aliases inline (`/help, /h`) and subcommand rows beneath (`/session` > `new`/`list`/`load`/`delete`/`save`), all aligned to a computed description column
- `/session` (no args) reuses the shared subcommand metadata instead of a hardcoded usage block
- `/tool` command respects tool policy - listing shows only allowed tools, execution routes through `_run_tool()` (deny rejection + confirm prompts)
- `Session.to_dict()` and the agent loop unchanged - confirm prompts and tool status remain ephemeral REPL UI, never persisted
- `Config` shallow-copied `DEFAULT_CONFIG`, sharing the nested `tools.deny`/`tool_permission` lists/dicts across instances - mutations (e.g. `/config tools.deny -a ...`) leaked into later sessions, now deep-copied on load and reload

## v0.6.0 - 2026-08-02

- `/tool <name> <json-args>` slash command - generic thin wrapper executing any registered tool via the same `ToolRegistry` the model uses, no args lists registered tools
- `tests/test_tool_registry.py` - registry metadata tests: `refine_required()` for `web_search` vs `fetch_page`/unknown
- `tests/test_commands.py` - `/tool` dispatch tests: registry execution, name listing, disabled path, invalid JSON
- Unified streaming agent loop (`_agent_loop()` in `chat.py`) - a single SSE stream per turn replaces the two-phase non-streaming decision + streaming call, `tool_calls` events are handled mid-stream, eliminating the double-call cost when no tools are used
- `_StreamRenderer` in `chat.py` - stateful streaming display (thinking markers, markdown, `<<<` prefix) extracted from the old `_stream_response` and reused across loop rounds
- `OllamaProvider.chat()` now accepts `tools`, forwards them in the stream payload, and accumulates fragmented `delta.tool_calls` into a `tool_calls` event
- `tests/helpers.py` - shared `make_chat()` builder for ChatLoop tests
- `tests/test_agent_loop.py` - loop-level tests: no-tools single round trip, thinking excluded from persisted content, error bail, empty stream
- `tests/test_ollama_provider.py` - provider streaming tests: fragmented tool-call accumulation, `done`/`thinking` events, `tools` in payload, error passthrough
- `ToolRegistry.register()` accepts `refine` metadata, `refine_required()` lookup added - `web_search` registered with `refine=True`, and `_execute_tool_calls()` now refines via metadata instead of special-casing the `web_search` name
- `BaseProvider.chat()` signature gains `tools: list[dict] | None = None`
- `_handle_message()` branches collapse onto `_agent_loop()`, `chat_nonstreaming()` is now used only by `_refine_query()`
- `tests/test_tool_calling.py` rewritten against the streaming event generator
- `_chat_with_tools()`, `_stream_response()`, `_output_content()` and `_response_start` from `chat.py`
- `/search` and `/web` slash commands - model tool-calling and `web_search` auto mode cover searching

## v0.5.0 - 2026-07-28

- `_TextExtractor` class in `tools/builtins.py` - stdlib HTMLParser-based text extraction for `fetch_page`
- Test `test_empty_stream_falls_back_to_nonstreaming_content` - verifies fallback saves non-streaming content when streaming returns empty
- `Session.to_dict()` filters out `role: tool` messages - session files only contain REPL-visible messages (user, assistant, command, system)
- Final assistant response missing from session when streaming returned no tokens - fall back to non-streaming result content when `_stream_response()` returns empty
- `fetch_page` returned raw HTML/JS/CSS noise - replaced regex tag-stripping with `_TextExtractor` (HTMLParser) that drops `<script>`, `<style>`, `<svg>`, `<noscript>` and extracts clean visible text
- Session files stored raw tool-result content that was never displayed in the REPL - filtered `role: tool` messages from serialized output, assistant `tool_calls` (web_search, fetch_page declarations) still documented

## v0.4.0 - 2026-07-28

- 3 new test cases: empty-content, multiple tool calls, and API error path (now 7 tests total)
- Tool-call messages (assistant tool_calls + tool results) lost when streaming produced empty content or an exception occurred - wrapped `_chat_with_tools()` and `_stream_response()` in `try/finally` so session is always persisted
- `_chat_with_tools()` no longer skips `_stream_response()` when `chat_nonstreaming` returns empty/null content - final response is always streamed
- Session file rename left JSON `name` field stale - added `session_auto_save()` after rename so the file always has the correct session name

## v0.3.0 - 2026-07-28

- Auto-session naming: first user message auto-names the session (sanitized, truncated to 40 chars). Renames the `.json` file on disk
- Markdown-aware streaming: code blocks in cyan, inline code in green, bold text rendered with ANSI bold. Disabled by default (`markdown_streaming: false`). Enable via config.
- Thinking/reasoning token detection: provider-level `reasoning_content` field (DeepSeek R1, o1, o3). Configurable via `show_thinking` (default `true`)
- Error handling: `_post()`, `chat_nonstreaming()`, `chat()`, `_chat_with_tools()`, and `list_models()` now catch `HTTPError` (auth 401, server 500) and `URLError` (network, timeout) gracefully - errors print in red, REPL continues
- `_chat_with_tools()`: when no tools are used, now calls `_stream_response()` for live token output instead of dumping the full response at once
- `query_refine` config system: when enabled, short web_search queries (≤ `query_refine_min_words` words) are auto-refined via a lightweight model call with `query_refine_context` recent messages as context. Configurable via `query_refine`, `query_refine_min_words` (default 3), `query_refine_context` (default 4)
- `tool_status_visible` config option (default `true`): when `false`, hides dimmed `[tool: args]` status lines during tool execution
- Mock test suite for tool calling (`tests/test_tool_calling.py`): 4 offline tests covering no-tools, single-tool, unknown-tool error, and force-search paths
- Markdown streaming now off by default, the state machine was unreliable on real streaming output
- Removed `...` as thinking marker/closer (too many false positives in normal text)

## v0.2.0 - 2026-07-27

- Auto-search mode: set `web_search: true` in config to search on every message
- Search results displayed as compact list, injected as AI context for grounded responses
- `/search <query>` and `/web <query>` commands
- `web/display.py` - `format_results()` for terminal, `format_context()` for AI context injection
- `web/search.py` - `DDGResultParser` (HTMLParser), search endpoint at `lite.duckduckgo.com`
- Web search: DuckDuckGo Lite via `html.parser` - `/search <query>` and `/web <query>` commands
- Config default: `tool_calling: true`
- `/search` command integrated with tool calling (uses `_chat_with_tools(force_search=...)`)
- `_show_tool_status()` - dimmed `[web_search: "query"]` status during tool execution
- `_chat_with_tools()` - decision loop that executes tool calls and injects results
- Ollama provider: refactored payload generation, `chat_nonstreaming()` with `tools` support
- `BaseProvider.chat_nonstreaming()` - returns `{role, content, tool_calls, finish_reason}`
- `tools/builtins.py` - `web_search` and `fetch_page` tools
- `tools/registry.py` - decorator-based tool registration (OpenAI function calling format)
- Tool calling system: two-phase chat (non-streaming tool decision > stream final content)

## v0.1.0 - 2026-07-27

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
