# Replio - Agent Guide

## Project

A terminal-based **agentic REPL core**. The model is the planner. The tool registry is how it acts. It is a zero-dependency Python app (`stdlib only`) built around a **single agent loop**: one SSE stream per turn where the model either emits content or requests tool calls, which the loop executes and feeds back until the model answers.

Multi-provider chat, web search, sessions, slash commands, machine access, personas and delegation, and plugins are all capabilities on top of that core.

## Tech Stack

- Python >=3.10, **stdlib only** (no external dependencies)
- `readline` - input history + tab completion for slash commands
- `urllib.request` - HTTP + SSE streaming
- `urllib.error` - HTTP error handling
- `json` / `pathlib` / `os` - config and session storage

## Architecture: Agentic Core

The agentic core has three layers:

1. **Agent loop** (`engine.py`) - the headless core. Each turn runs a single streaming request. The provider's `chat()` is a generator yielding events, and the engine reacts:
   - `thinking` / `token` - streamed to the sink (`UISink`), `ReplUI` renders ANSI thinking + optional markdown, `HeadlessUI` logs to stderr / buffers for JSON
   - `tool_calls` - append the assistant message, execute each call, append `tool` results, then continue the loop
   - `error` - record + print and bail
   - `done` - persist the assistant message (timestamp/duration/model) and stop

   One stream, one round trip when no tools are used. `chat_nonstreaming()` is reserved for query refinement, not the main path. The loop is front-end agnostic: `ChatLoop` (REPL), `replio run` (CLI), and `replio serve` (HTTP) all call `Engine.chat(text) -> TurnResult`. The `<thinking>` marker split lives in the engine so thinking stays separate from content.

2. **ToolRegistry** (`tools/registry.py`) - the **single dispatch point**. The model invokes tools via OpenAI function calling, slash commands are thin wrappers that call the same `execute()`. The loop never special-cases tool names - per-tool behavior comes from registration metadata (`refine`, `permission_fn`, `note`, later `confirm`). The `delegate` tool (`tools/delegate.py`) is a core tool that runs a task under a persona by spawning an in-process sub-`Engine` (`Engine.run_subagent`) - the same agent loop, its own `delegate_<persona>_<ts>` session, a quiet `NullUI`. Its permission is a per-invocation `permission_fn` resolved per persona.

3. **Commands** (`commands/`) - user-facing affordances. A command either wraps a tool or performs a local action (`/model`, `/session`).

Providers (`providers/`) are OpenAI-compatible `/v1/chat/completions` backends that implement the event-generator `chat()` contract. A fuller treatment of the core, UI sinks, and front-ends is in `docs/architecture.md`.

### Project Structure

```
Replio/
├── pyproject.toml
├── AGENTS.md
├── README.md
├── TODO.md
├── CHANGELOG.md
├── tests/
│   └── test_tool_calling.py   # Mock tests (no network/API key needed)
├── src/replio/
│   ├── __init__.py
│   ├── __main__.py          # python -m replio
│   ├── main.py              # CLI arg parsing + bootstrap (default REPL, run, serve)
│   ├── cli.py               # `replio run` / `replio serve` headless entry points
│   ├── config.py            # JSON config (global + local merge)
│   ├── models.py            # global model registry - models.json (connections + keys)
│   ├── personas.py          # Persona registry - bundled/global/local personas.json merge + tags
│   ├── bundled_personas.json # bundled default personas (8, two pre-carved teams)
│   ├── engine.py            # Headless agent core - Engine + TurnResult + run_subagent
│   ├── chat.py              # ChatLoop(Engine) - REPL shell with readline
│   ├── ui.py                # UISink - ReplUI / HeadlessUI / NullUI renderers
│   ├── server.py            # stdlib HTTP JSON API (POST /chat, GET /sessions, GET /health, GET /version)
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── base.py          # Abstract provider (OpenAI-compatible)
│   │   └── ollama.py        # Ollama cloud via /v1/chat/completions
│   ├── sessions/
│   │   ├── __init__.py
│   │   └── manager.py       # Session CRUD (JSON files)
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── registry.py      # Command registration + dispatch
│   │   └── builtins.py      # /help, /connect, /model, /session, /plugins, etc.
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── registry.py      # Tool registration + dispatch (OpenAI function calling)
│   │   ├── policy.py        # ToolPolicy - allow/ask/deny permissions + path scoping
│   │   └── delegate.py      # Core delegate tool - persona sub-agents via per-invocation policy
│   ├── plugins/
│   │   ├── __init__.py
│   │   └── manager.py       # PluginManager - discovery, manifest/compat, install/update/uninstall
│   └── utils/
│       ├── __init__.py
│       └── http.py          # urllib-based SSE streaming
└── plugins/                 # bundled plugins (shipped as replio.plugins.bundled)
    └── replio-core-exec/        # run_command
    ├── replio-core-fs/          # read_file, list_dir, write_file, glob, grep
    ├── replio-core-websearch/   # web_search, fetch_page + search service
```

## Conventions

### Code Style
- No external dependencies, stdlib only. Plugins may opt into third-party deps via their manifest, but the core never depends on them
- No comments in code
- Type hints required for all function signatures
- Use `from __future__ import annotations` if needed for `|` syntax
- Prefer `pathlib.Path` over `os.path`
- ANSI escape codes for terminal coloring (no `rich`/`colorama`)
- `\001` / `\002` readline markers around ANSI codes in prompts

### Architecture Rules
- One agent loop, one SSE stream per turn - no separate non-streaming decision round
- `ToolRegistry` is the single dispatch point: commands call tools, they never reimplement them
- No tool-name special-casing in the loop - use registration metadata instead
- `BaseProvider.chat()` is a generator yielding events: `thinking`, `token`, `tool_calls`, `error`, `done`
- `BaseProvider` uses OpenAI-compatible `/v1/chat/completions` format
- Config: global (`~/.config/replio/config.json`) > local (`.replio/config.json`) merge, local wins
- Sessions stored as `.replio/sessions/<name>.json`
- Slash commands registered via `@registry.register()` decorator
- Tools registered via `@tool_registry.register()` decorator (OpenAI function calling format)

### Doc Conventions
- `TODO.md` has three zones. Ideas are plain bullets at the very top (no header, no checkbox - they evolve over time), followed by `## Open` (defined `[ ]` tasks) and `## Done` (`[x]` items, separated by `---`). Within `## Open` and `## Done`, items are sorted newest-first so new tasks are added at the top of their zone without reorganizing, nested sub-bullets are preserved (e.g. machine tools, tool policy). Completed items stay in `## Done` and are never moved to an archive. `## Done` entries are short one-liners - detailed change descriptions live in `CHANGELOG.md` under the matching version. As a soft rule, keep each `## Done` entry to a single line of at most 100 characters (shorter is better - trim detail rather than wrap or exceed).
- `CHANGELOG.md` is grouped by **versions**, newest at the top - new `## vX.Y.Z - YYYY-MM-DD` sections go above previous ones, so the latest changes are readable with `head`. Entries under each version form a **single flat bullet list, newest first** (no `### Added`/`### Changed`/`### Removed` grouping).
- After completing a planned task: mark it `[x]` in `TODO.md` and add entries under the current version section at the top of `CHANGELOG.md` (start a new version section first if none exists).
- Keep both files in sync with actual project state.
- Keep `version` in `pyproject.toml` in sync with the current version in `CHANGELOG.md` - bump it whenever a release section is started or finalized.
- Use only ASCII punctuation and glyphs in docs. Avoid typographic Unicode characters: em-dashes (`—`), en-dashes (`–`), smart/curly quotes (`‘ ’ “ ”`), the single-character ellipsis (`…`), non-breaking spaces, and similar substitutes. Use plain hyphens (`-`) or ASCII three dots (`...`) instead, and split clauses with periods or commas rather than semicolons (`;`). Inline code and quoted strings may keep non-ASCII only when they reproduce literal runtime output (e.g. the `…` truncation marker).

## Extension Points

### Adding a Tool
1. Use the `@registry.register(name, description, parameters)` decorator in the plugin/module where the tool belongs
2. `parameters` follow the OpenAI function calling JSON schema format. The handler receives keyword arguments matching the schema and returns a string (the tool result injected into the conversation)
3. Add optional metadata for loop behavior and permissions: `refine`, `category`, `permission`, `path_arg`, `key_arg`, `glyph`/`verb`, `status`, `echo`, `permission_fn`, `aliases`, `param_aliases`, `note` - full reference in `docs/tools.md`
4. `ToolRegistry.execute()` passes only args declared in the tool's schema - undeclared and `null`-valued args (e.g. a hallucinated `recursive`, or `depth: null`) are dropped, never forwarded to the handler
5. `aliases` (extra tool names resolving to this tool, e.g. `read`/`view` for `read_file`) and `param_aliases` (caller-side param synonyms mapped onto declared params, e.g. `{'cursor': 'offset'}`) let the registry absorb model-dialect tool and argument names without advertising them in the schema. `/tool`, `/help`, policy, confirm, and glyphs work through aliases unchanged

### Machine Access & Permissions
- `ToolPolicy` (`tools/policy.py`) is the single permission resolution point. The loop and `/tool` both route through it, so never special-case tool names for permission logic
- Actions: `allow` (no prompt), `ask` (y/N confirm in the loop via `_confirm_tool`), `deny` (tool filtered from the provider schema and refused on direct calls)
- Precedence: name-level `deny` / allow-whitelist > category action from `tool_permission` > per-invocation resolver (`permission_fn`, refined from the tool's current arguments - e.g. `delegate` resolves per persona) > worktree escalation (read/write/list outside the worktree becomes `ask`)
- The worktree is the directory holding the local `.replio/` - i.e. the launch directory, or `--path`. Launching from `~` makes the whole home directory the worktree, so subdirectories (including other projects) do **not** escalate. Launch inside the project or pass `--path` for project-scoped prompting
- `bash: ask` by default - every `run_command` confirms. Set `tool_permission.bash = "allow"` to disable prompting. `delegate` defaults to `allow` (runs without a prompt), refined per persona: a configured persona uses its own `tool_permission` (set `delegate: "ask"` on a persona to confirm), a persona outside the registry is denied
- Delegation (`run_subagent`) builds an in-process sub-`Engine` with the persona's prompt, model override, and merged `tool_permission`, forces mode `build`, shares the caller's provider/plugin manager/worktree, and runs with `NullUI` - ask-gated tools auto-deny, so a sub-agent's effective permissions are exactly its carve. Sub-agent results echo via `delegate_echo` (default on); each sub-agent persists its own `delegate_*` session
- Confirm prompts and tool status are ephemeral REPL UI - never persisted to session files. The permission decision itself (granted / declined / denied) is recorded in the session `permissions` audit array
- Full policy flow and registration metadata in `docs/tools.md`. Threat model in `docs/security.md`
- Sandboxed exec (namespace/container isolation) is planned future work (see TODO). Per-agent permission profiles landed with personas (`tool_permission` on each persona)

### Adding a Provider
1. Create `src/replio/providers/<name>.py`
2. Subclass `OpenAICompatibleProvider`, set `DEFAULT_BASE_URL` / `DEFAULT_MODEL` (override `_headers()`/`_payload()` only for non-standard auth or bodies)
3. Add the class to the `PROVIDERS` dict in `providers/__init__.py`
4. Add a hostname match in `detect_provider()` so `/connect` auto-selects it

The chat() event contract and full provider reference are in `docs/providers.md`.

### Adding a Slash Command
1. Open `commands/builtins.py`
2. Use `@registry.register('name', aliases=['a1', 'a2'])` decorator
3. Handler receives one string argument (the text after the command name)
4. If the command performs a tool action, call `chat_loop._tool_registry.execute(name, args)` rather than reimplementing it

### Adding a Plugin
Plugins are external repositories - never modify the core to add optional functionality:
1. Create a plugin directory with a `manifest.json` (`name`, `version`, `replio_version` semver range, `python` range, `entry` default `plugin.py`, `requires` third-party deps, `provides`) and an entry module
2. The entry module may define `register_tools(registry)`, `register_providers(providers: dict)`, `register_commands(commands)`, and `register_services(services)` - same decorators as core builtins
3. Import third-party deps lazily **inside** tool functions, the core never imports them
4. Install via `/plugins install <git-url|path>` or `replio plugins install`. Activation is the `plugins` config list (empty = all), and `install`/`uninstall`/`enable`/`disable` maintain it automatically
5. See `docs/plugins.md` for the full manifest schema, compatibility contract, and management commands
6. Bundled plugins live in the repo `plugins/` dir (shipped as `replio.plugins.bundled`) - add a new bundled plugin there + to the `plugins` config default, never to the core

### Future: Plugin sources
Plugins currently install from git URLs or local paths into the plugin roots. Shared/per-plugin virtualenv dependency isolation and a PyPI entry-point source are planned future work (see TODO).

## Roadmap

- **Phase 0** - Unified streaming agent loop (single SSE stream, `tool_calls` events)
- **Phase 1** - Unified dispatch (slash commands > same `ToolRegistry`, generic refinement)
- **Phase 2** - Machine access (read/write/exec tools, tool policies, `confirm`-gated exec)
- **Phase 3** - Personas - landed: persona catalog (`bundled_personas.json` + global/local `personas.json` merge), `/persona` (list/show/new/remove, tag filter), tags, per-persona `tool_permission`. Remaining: interactive `/agent` command
- **Phase 4** - Delegation - landed (core): `delegate` tool > in-process sub-`Engine` (`run_subagent`), per-persona permission resolver, `delegate_echo`. Remaining: auditor agents, generate > check > correct, jobs/team orchestration, delegation progress/focus in the REPL
- **Phase 5** - Plugins (tools + providers + commands installable, directory-based)
  - `PluginManager` discovers plugins in bundled `replio.plugins.bundled`, `~/.config/replio/plugins/`, and `.replio/plugins/` (local wins), validates the manifest (`replio_version`/`python` ranges), imports entry modules once, and hooks tools/providers/commands/services into the live registries
  - Management: `/plugins` and `replio plugins` - `install`/`update`/`uninstall`/`enable`/`disable`. Activation is via the `plugins` config list (empty = all)
  - Plugin third-party deps are lazy (imported inside plugin functions) - the core stays stdlib-only
  - Built-in web + machine tools ship as bundled plugins (`replio-core-websearch`, `replio-core-fs`, `replio-core-exec`). Future: per-plugin venv isolation, PyPI entry-point source, externalizing the bundled plugins

Implement one phase at a time. Docs-first: restructure planning docs, then build the phase, mark it `[x]`, and log it in `CHANGELOG.md`.

## Config Schema

Full schema and defaults are in `docs/config.md`. Notable edge cases:

- `max_tokens` defaults to `8192` - the cap sent to the provider, which overrides low provider-side defaults (e.g. Ollama's 2048). Set it to `0` to omit it from the provider payload, so the provider's own default applies. Hitting the limit prints a warning (distinguishing a configured cap from the provider's default) and logs a session `errors` entry.
- `plugins` lists the plugins to load, and the bundled plugins are in the default. An empty list loads all discovered plugins. `plugins.enabled`/`plugins.deny` from earlier versions are migrated automatically.

## Testing

Run tests before committing changes to verify core logic isn't broken. The suite is stdlib `unittest` with mock providers (no network, no API key). Commands and the per-file coverage map are in `docs/testing.md`.

## Sessions

Sessions are complete, append-only logs - every message, tool call + result, reasoning, and error is persisted, and entries are **never removed** (compaction only trims the provider context). The full schema - file location, message fields per role, `errors`, serialization-time transforms (`noise_tools`, `session_tool_max_chars`), provider-context preparation, and compaction - is in `docs/session.md`.
