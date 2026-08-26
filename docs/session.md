# Sessions

Sessions are complete, append-only conversation logs. Every message, tool call and its result, reasoning, and error is persisted as JSON under the project's `.replio/sessions/` directory. Entries are never removed - compaction only trims the provider context, never the log.

## Where sessions live

Each session is one JSON file: `.replio/sessions/<name>.json`, next to the local `.replio/config.json`.

Names are either explicit (`/session new <name>`, `/session load <name>`, `replio run --session-id <name>`) or auto-generated as `ses_<timestamp>_<first-message-slug>`, for example `ses_20260817_120000_what_is_oee`.

Session files carry a type prefix so the three kinds stay distinguishable at a glance:

| Prefix | Kind | Example |
|--------|------|---------|
| `ses_` | Interactive/auto sessions | `ses_20260817_120000_what_is_oee.json` |
| `job_` | Jobs - one fresh file per run | `job_20260826_110230_nightly_report.json` |
| `sub_` | Delegation sub-agents | `sub_20260817_120100_researcher.json` |

Delegation writes each sub-agent's log as its own session: `sub_<ts>_<persona>` (e.g. `sub_20260817_120100_researcher`; the legacy `delegate_<persona>_<ts>` names remain readable). These live in the same `.replio/sessions/` directory and are regular sessions - listed by `/session list` (annotated with their parent), exportable, loadable - so lead and sub-agent logs stay separate and complete.

## Managing sessions

| Command | Purpose |
|---------|---------|
| `/session new <name>` | Create and switch to a new session |
| `/session list` | List saved sessions |
| `/session preview <name>` | Structural preview (roles, tool names) without switching |
| `/session load <name>` | Load a session (with compaction offer if it has a summary) |
| `/session delete <name>` | Delete a session |
| `/session save` | Save the current session |
| `/session export <name> [out]` | Export a session to Markdown |
| `replio run --session-id <name>` | Load or create a session from headless mode |

The current session is auto-saved after every message and command, so nothing is lost on exit.

## Exporting to Markdown

`/session export <name>` renders any saved session as a Markdown transcript. It reads the persisted log directly (`read()`, not `load()`), so the current session is never switched and the source file is left untouched.

The default output is `.replio/exports/<name>.md`, next to the `sessions/` directory. A second argument overrides the path (`/session export <name> out.md`), and `-` prints the transcript to stdout instead of writing a file. The command tab-completes session names.

The export is the full, auditable log: each message becomes a `### <Role>` section with its timestamp, assistant meta (provider/model/duration) and thinking, tool calls and results as fenced code blocks (with tool `analysis`), `command` records, compaction summaries (with the trimmed context boundary), and a final `## Errors` section. Because it renders the persisted form, serialization-time transforms (`noise_tools` markers, `session_tool_max_chars` truncation) carry through as they appear in the file.

The headless CLI `replio export <name> [--out <file>]` reuses the same renderer for scripts and CI - `--out -` prints to stdout, the default matches the slash command (`.replio/exports/<name>.md`).

## File structure

```json
{
  "name": "20260817_120000_what_is_oee",
  "created_at": "2026-08-17T12:00:00+00:00",
  "updated_at": "2026-08-17T12:05:15+00:00",
  "messages": [],
  "errors": [],
  "permissions": [],
  "parent_id": "",
  "sub_sessions": []
}
```

| Key | Type | Description |
|-----|------|-------------|
| `name` | string | Session name, matches the filename |
| `created_at` | string | ISO 8601 UTC timestamp of creation |
| `updated_at` | string | ISO 8601 UTC timestamp, bumped on every appended message |
| `messages` | array | The conversation log, append-only |
| `errors` | array | Turn-level errors (provider, network, agent loop) |
| `permissions` | array | Audit log of tool permission decisions (see below) |
| `parent_id` | string | Name of the session this one was spawned from (sub-agent sessions set it; empty otherwise) |
| `sub_sessions` | array | Names of sessions spawned from this one (delegations; the delegate sets a sub-agent's `parent_id` here) |

`/session preview` prints the `parent` and `sub-sessions` links; `/session list` annotates `sub_*` (and legacy `delegate_*`) children with their parent.

## Message schema

Every message has at least `role`, `content`, and `timestamp` (ISO 8601 UTC). The fields beyond those depend on the role.

| Field | Applies to | Description |
|-------|-----------|-------------|
| `role` | all | `user`, `assistant`, `tool`, `command`, or `system` |
| `content` | all | Message text, or `null` for an assistant tool-call message |
| `id` | all | Stable message identifier (`msg_<hex>`), auto-assigned on creation |
| `timestamp` | all | ISO 8601 UTC timestamp |
| `duration` | `assistant` | Response time in seconds |
| `model` | `assistant` | Model that produced the response |
| `provider` | `assistant` | Provider that served it |
| `thinking` | `assistant` | Reasoning text preceding the answer or tool call, excluded from `content` |
| `reasoning` | `assistant` | The `reasoning` config value in effect for this message (how reasoning was requested: `false`/`"off"` or an effort value) |
| `mode` | `assistant` | The agent `mode` config value in effect for this message (`build`, `plan`, or a custom mode) |
| `tool_calls` | `assistant` | OpenAI function-call objects requested by the model |
| `tool_call_id` | `tool` | ID linking the result to the originating `tool_calls` entry |
| `tool` | `tool` | Name of the tool that produced the result |
| `analysis` | `tool` | Optional one-line model insight (`tool_analysis` config) |
| `result` | `command` | Compaction summary, on the `/compact` record |
| `compact_from` | `command` | Index into `messages` where the kept portion starts |

### Examples

A plain user/assistant exchange:

```json
{"role": "user", "content": "What is OEE?", "timestamp": "2026-08-17T12:00:00+00:00"},
{"role": "assistant", "content": "OEE is Overall Equipment Effectiveness...", "timestamp": "2026-08-17T12:00:05+00:00", "duration": 4.8, "model": "llama3.2", "provider": "ollama", "thinking": "The user asks a definitional question, answer directly."}
```

A tool call and its result:

```json
{"role": "assistant", "content": null, "tool_calls": [{"id": "call_xxx", "type": "function", "function": {"name": "web_search", "arguments": "{\"query\": \"latest Python release\"}"}}], "timestamp": "2026-08-17T12:01:00+00:00", "thinking": "I need current data, search first."},
{"role": "tool", "tool_call_id": "call_xxx", "content": "Web search results...", "timestamp": "2026-08-17T12:01:03+00:00", "tool": "web_search", "analysis": "Pages about recent Python releases - 3.13 is the latest."}
```

A command and a compaction record:

```json
{"role": "command", "content": "/model llama3.3", "timestamp": "2026-08-17T12:02:00+00:00"},
{"role": "command", "content": "/compact", "timestamp": "2026-08-17T12:03:00+00:00", "result": "Summary of the earlier conversation...", "compact_from": 8}
```

A `command` message with a `result` is a compaction record: `result` holds the summary and `compact_from` is the index into `messages` where the kept portion starts. The system prompt set at REPL start and search contexts injected by `web_search: true` mode are recorded as `system` role messages.

## Errors

Turn-level failures are appended to the `errors` array, separate from the message log:

```json
{"code": 401, "message": "Unauthorized", "timestamp": "2026-08-17T12:40:00+00:00"}
```

`code` is the HTTP status where one exists, otherwise `0`. Errors include provider auth/network failures, stream EOF or empty completions, `max_tokens` truncation, and unexpected exceptions from the agent loop.

## Permissions

Every tool permission resolution is recorded to the `permissions` array, making the log an audit trail of what the agent was allowed to do:

```json
{"tool": "run_command", "action": "ask", "decision": "granted", "path": "/home/me/proj", "timestamp": "2026-08-17T12:40:00+00:00"}
{"tool": "write_file", "action": "deny", "decision": "denied", "path": "/home/me/proj/a.md", "timestamp": "2026-08-17T12:41:00+00:00"}
```

| Field | Description |
|-------|-------------|
| `tool` | The tool name |
| `action` | The resolved policy action: `allow`, `ask`, or `deny` |
| `decision` | The outcome: `granted` (ran), `declined` (user refused an `ask`), or `denied` (blocked by policy) |
| `path` | The tool's `path_arg` value when the tool has one (e.g. the file or command target) |
| `timestamp` | ISO 8601 UTC timestamp |

Per-invocation (resolver-based) actions are recorded the same way - for example `delegate` logs the action resolved from the target persona, so which delegation was allowed, asked, or denied is auditable. Entries are append-only and never removed. Recording is always on - there is no config switch, so the log stays a reliable audit record.

## Append-only semantics

Messages and errors are only ever appended. Compaction stores the summary in a new `command` record and leaves the earlier messages in place. Loading a session never rewrites history. The only transformations happen at serialization time (below), never to the in-memory log.

An `assistant` message is written whenever the turn produced content **or** thinking - so a truncated mid-reasoning turn still persists its thinking, and a reasoning-only turn (thinking present, no content) is recorded rather than lost. Empty turns (no content, no thinking) persist nothing.

## Serialization-time transforms

Two config keys reshape `tool` message content when the session is written to disk, without touching the stored messages themselves:

- **`noise_tools`** (default `["fetch_page"]`) - results of the listed tools are replaced with `[<tool> result excluded from log, see tool call above for parameters]`, keeping noisy results out of session files while preserving the parameters in the tool call above.
- **`session_tool_max_chars`** (default `0` = unlimited) - caps persisted tool-result content to N characters, appending `… (truncated from <len> chars)`.

## Preparing the provider context

The provider payload is prepared from the log by `_provider_messages()`:

- `command` role messages are dropped.
- Compaction records (`command` with `result`) become a `system` summary: `Summary of earlier conversation:\n\n<summary>`.
- Dangling `tool` messages (whose `tool_call_id` is no longer matched by a declared `tool_calls` entry, e.g. at a `compact_from` boundary) are skipped.
- Everything else is passed through in order.

For compaction, tool results are folded back into the summarized context as `[tool result] <content>` user messages so the summary can carry forward what the tools found.

## Compaction

`/compact` summarizes the earlier conversation and trims the provider context, controlled by `compact_keep` (default 4 = messages kept at the tail). The summary is stored in the `result` of a `command` record with a `compact_from` boundary, so the full history stays in the log while only the summary is sent to the model going forward.
