# Architecture

Replio is a terminal-based agentic REPL core: the model is the planner, the tool registry is how it acts. It is a zero-dependency Python app (stdlib only) built around a **single agent loop** - one SSE stream per turn where the model either emits content or requests tool calls, which the loop executes and feeds back until the model answers.

## The three core layers

1. **Agent loop** (`src/replio/engine.py`) - the headless core. Each turn runs a single streaming request. The provider's `chat()` is a generator yielding events, and the engine reacts:
   - `thinking` / `token` - streamed to the sink (`UISink`)
   - `tool_calls` - appends the assistant message, executes each call, appends `tool` results, then continues the loop
   - `error` - records and prints, then bails
   - `done` - persists the assistant message (timestamp/duration/model) and stops

2. **ToolRegistry** (`src/replio/tools/registry.py`) - the single dispatch point. The model invokes tools via OpenAI function calling. Slash commands are thin wrappers calling the same `execute()`. The loop never special-cases tool names - per-tool behavior comes from registration metadata. See [tools.md](tools.md).

3. **Commands** (`src/replio/commands/`) - user-facing affordances. A command either wraps a tool or performs a local action (`/model`, `/session`).

Providers (`src/replio/providers/`) are OpenAI-compatible `/v1/chat/completions` backends implementing the event-generator `chat()` contract. See [providers.md](providers.md).

## Engine and TurnResult

`Engine.chat(text) -> TurnResult` is the front-end-agnostic entry point. The REPL (`ChatLoop`), the headless CLI (`replio run`), and the HTTP API (`replio serve`) all call it. A `TurnResult` carries:

```python
{content, thinking, tool_calls, errors, duration, usage,
 model, provider, session, status}
```

`status` is `ok`, `error`, `empty`, or `truncated`. Sessions are addressed from any front-end via `Engine.load_or_create_session(name)`.

## One stream, one round trip

When no tools are used, a turn is a single streaming request - no separate non-streaming decision round. `chat_nonstreaming()` is reserved for auxiliary decisions: query refinement, tool-result analysis, and compaction. The `<thinking>` marker split lives in the engine so thinking stays separate from content in JSON results and session logs.

## UI sinks

The loop renders through a `UISink`, an interface of methods the loop calls as events happen (`token`, `thinking`, `tool_status`, `activity`, `footer`, `confirm`, `error`, ...):

| Sink | Purpose |
|------|---------|
| `ReplUI` | Terminal REPL: ANSI streaming, dimmed thinking, optional markdown, confirm prompts, footer stats |
| `HeadlessUI` | `run` / `serve`: stderr diagnostics, auto-approve/deny confirm policy, never blocks on stdin |
| `NullUI` | Silent, for tests |

`ReplUI`'s markdown rendering (code blocks, inline code, bold) is a lightweight token-level state machine in `src/replio/ui.py`, gated by the `markdown_streaming` config.

## Front-ends

| Front-end | Entry | Mode |
|-----------|-------|------|
| REPL | `replio` | Interactive shell with readline history, tab completion, slash commands |
| CLI | `replio run` | One-shot headless chat, JSON or text output, for scripting and CI/CD |
| HTTP | `replio serve` | Stdlib `ThreadingHTTPServer` JSON API over the same engine |

Agents talk to each other over the same `POST /chat` API that `replio serve` exposes, which is how fleets and swarms compose. See [fleet.md](fleet.md), [swarm.md](swarm.md), and [api.md](api.md).

## Sessions

Every turn appends to a session - a complete, append-only JSON log of messages, tool calls and results, reasoning, and errors. The provider payload is prepared from the log by `_provider_messages()`. See [session.md](session.md).

## Plugins

Plugins extend the core with tools, providers, commands, and services without changing it. `PluginManager` discovers plugins in the bundled, global, and local roots, validates manifests, and hooks them into the live registries. The core stays stdlib-only. Plugin dependencies are imported lazily. See [plugins.md](plugins.md).

## Source layout

```
src/replio/
├── __main__.py          # python -m replio
├── main.py              # CLI arg parsing + bootstrap (REPL, run, serve, plugins)
├── cli.py               # headless entry points
├── config.py            # JSON config (global + local merge)
├── engine.py            # headless agent core - Engine + TurnResult
├── chat.py              # ChatLoop(Engine) - REPL shell with readline
├── ui.py                # UISink - ReplUI / HeadlessUI / NullUI
├── server.py            # stdlib HTTP JSON API
├── providers/           # OpenAI-compatible chat providers
├── sessions/            # session CRUD (JSON files)
├── commands/            # command registry + builtins
├── tools/               # tool registry + tool policy
├── plugins/             # plugin manager
└── utils/               # urllib-based SSE streaming
```

## Extension points

- **Adding a tool** - see [tools.md](tools.md)
- **Adding a provider** - see [providers.md](providers.md)
- **Adding a command** - commands are registered via `@registry.register()`. If the command performs a tool action it calls the tool registry rather than reimplementing it
- **Adding a plugin** - see [plugins.md](plugins.md)