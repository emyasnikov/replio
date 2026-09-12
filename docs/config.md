# Configuration

Config is a single JSON object read from two files and merged per key, with project-local values winning:

1. **Global** - `~/.config/replio/config.json` (user-wide defaults, credentials).
2. **Local** - `.replio/config.json` in the project path (project overrides).

Every process merges them in memory. Nothing is distributed to folders. Writes default to the **local** file and hold only the keys you selected - a save never re-writes the merged config. API keys live outside the config, in the global provider registry (`~/.config/replio/providers.json`), managed through `/connect` (see [Models](#model-registry-not-config)).

```bash
# inspect in the REPL (origin: default/global/local)
/config
# set a value (project-local, Git-like default)
/config temperature 0.3
# set a structured value
/config tools.deny ["run_command", "web_search"]
# set a single line in the global config
/config --global temperature 0.2
# remove a project-local value, falling back to global/default
/config unset temperature
# remove a value from the global config
/config --global unset temperature
# reload from disk
/config reload
```

The `replio config` CLI does the same headlessly and is fully scriptable:

```bash
replio config get max_tokens --show-origin     # one or more values + where they come from
replio config set max_tokens 0                 # project-local
replio config set max_tokens 0 --global        # global file
replio config unset max_tokens                 # remove from project-local
```

Deleting a project's `.replio/config.json` reverts it to the global and built-in defaults. To keep settings across local deletions, set them globally with `--global` (accepted by both the REPL `/config` and the CLI), e.g. `/config --global provider ollama`, `/config --global model <model>`.

## Schema

| Key                         | Default                | Description                                                            |
|-----------------------------|------------------------|------------------------------------------------------------------------|
| `assistant`                 | `true`                 | Bind the REPL root to the `assistant_type` identity on startup. `false` leaves the root untyped (no injected identity). A non-empty `system_prompt` always wins over the type prompt |
| `assistant_type`            | `"assistant"`          | Agent type the REPL root binds to when `assistant` is on. Rebind to any type (e.g. `leader`, `composer`) or a local override of `assistant` |
| `ask_policy`                | *(see below)*          | Routing for the `ask` tool by kind (`permission`/`direction`)          |
| `auto_continue`             | `true`                 | On truncation (`finish_reason=length`) with a partial answer, re-request with a "continue" instruction and stitch the parts into one message |
| `auto_continue_max`         | `2`                    | Max continuation rounds per turn before reporting truncation     |
| `base_url`                  | `"https://api.ollama.com"` | Provider endpoint                                                  |
| `clear_screen`              | `true`                 | Clear the screen before the REPL banner                                |
| `compact_keep`              | `4`                    | Messages to keep when compacting the provider context                  |
| `confirm_timeout`           | `0`                    | Seconds a REPL confirm/ask prompt waits for input before auto-denying (`0` = wait forever). Applies at any depth, so an unattended-but-watched run still cannot freeze on a prompt. See [Unattended mode](#unattended-mode) |
| `connect_check`             | `true`                 | Test the provider connection on config changes: `/connect` probes before saving (broken values rejected unless confirmed), `/provider` warns on a failed probe. `false` skips all probes |
| `delegate_echo`             | `true`                 | When `delegate` runs, show the sub-agent's final answer and a sub footer (duration + completion tokens) in the REPL. Off hides the result. The footer shows only when on, alongside the sub-agent's own output |
| `footer_tokens`             | `["context"]`          | Token counts the footer shows, in order, joined by `/`. `context` = `<n> tokens` (context/input size, chars/4 fallback), `in`/`out`/`thinking` = `<n>t` from provider usage (unavailable counts skipped). Empty list hides the section |
| `glyph_lines`               | `true`                 | Typed `<glyph> <verb> <arg>` status lines for mapped categories. Off or unmapped categories fall back to the `[tool: arg]` oneliner |
| `glyph_params`              | `true`                 | Append tool call parameters to glyph status lines and confirm prompts (e.g. `← Read engine.py [offset=299, limit=85]`). Off for bare `<glyph> <verb> <arg>` |
| `grant_permission`          | `{}`                   | Delegation ceiling: the maximum category actions an engine may hand down to sub-agents. Empty means the engine's own `tool_permission` is the ceiling (no escalation). See [Permission authority](#permission-authority) |
| `list_dir_max_entries`      | `200`                  | Cap entries `list_dir` returns (`... (showing first N of M entries)` appended). `0` = unlimited |
| `markdown_streaming`        | `false`                | Basic markdown-aware streaming                                         |
| `max_tokens`                | `8192`                 | Output token cap sent to the provider. `0` = unset (provider default applies, e.g. Ollama caps at 2048). The default overrides low provider defaults |
| `max_team_depth`            | `2`                    | Maximum nested team runs (a `team` stage that itself runs a team). `0` = unlimited. Cycles are refused regardless. See [teams.md](teams.md#the-team-tool) |
| `mcp.servers`               | `[]`                   | MCP client server definitions (see [mcp.md](mcp.md) for the schema)     |
| `mcp_server.allow_ask`      | `true`                 | When serving MCP, run `ask`-policy tools (deferred to the client) vs refuse them |
| `mode`                      | `"build"`              | Active agent mode (`build`, `plan`, or a custom mode from `modes`) |
| `model`                     | `"llama3.2"`           | Model name. A `provider/model` ref (e.g. `opencode-go/deepseek-v4-flash`) unfolds to that provider and model. An unfolded model must be approved (see [Model refs and approval](providers.md#model-refs-and-approval)) |
| `noise_tools`               | `["web_fetch", "open", "fetch_page"]` | Tool results replaced by a marker in persisted sessions                |
| `plugins`                   | *(bundled)*            | Plugins to load. Empty = all discovered plugins load                   |
| `project_instructions`     | `"AGENTS.md"`          | Per-worktree instructions file auto-loaded into the system prompt (e.g. `AGENTS.md`, `CLAUDE.md`). `""` disables. Absent files skipped, content capped at 20000 chars |
| `prompt_role`               | `false`                | Prefix the REPL prompt with the active role when focus is not the root (e.g. `Assistant >>>`). `false` keeps the plain `>>>` |
| `provider`                  | `"ollama"`             | Provider name. Bundled provider plugins (`replio-core-ollama`, `-openai`, `-groq`, `-anthropic`, `-opencode`) register `ollama`, `openai`, `groq`, `anthropic`, `opencode`, `opencode-go`. `openai-compatible` is the generic fallback. External plugins can register more |
| `query_refine`              | `false`                | Auto-refine short web-search queries via a lightweight model call      |
| `query_refine_context`      | `4`                    | Recent-message context to inject into refinement                       |
| `query_refine_min_words`    | `3`                    | Minimum query length before refinement applies                         |
| `reasoning`                 | `"auto"`               | Request reasoning and control its token budget: `false`/`"off"` = none, `true`/`"on"`/`"auto"` = provider default, `"low"`/`"medium"`/`"high"` = explicit budget hint. Mapping is provider-specific (OpenAI `reasoning_effort`, Claude `thinking.budget_tokens`, Qwen `enable_thinking`) |
| `report.webhook`            | `""`                   | URL the bundled `replio-core-webhook` report connector POSTs a completed job run to (JSON). Empty = no out-of-band report. See [jobs.md](jobs.md#report-back) |
| `search_results`            | `5`                    | Number of search results to fetch                                      |
| `session_tool_max_chars`    | `0`                    | `0` = unlimited. Caps persisted tool-result content                    |
| `show_context_size`         | `true`                 | Dimmed context-size line after each response                           |
| `show_errors`               | `true`                 | Show a dimmed `! Error: ...` line (first line of the result) when a tool call fails. Off hides the line |
| `show_notes`                | `true`                 | Show a dimmed info line for soft tool results (e.g. `(empty file)`, `(no matches for "x")`). Off hides the line |
| `show_thinking`             | `false`                | Stream thinking/reasoning tokens dimmed. When off, thinking shows as an animated spinner plus a `+ Thought N.Ns` summary (display only - what is sent to the model is unchanged) |
| `show_thought_duration`     | `true`                 | When thinking is streamed (`show_thinking` on), print a dimmed `(Thought N.Ns)` line after each thinking block. Off hides it |
| `show_version`              | `true`                 | Show the version in the REPL banner                                    |
| `stream_retries`            | `2`                    | Extra attempts (after the first) when a provider stream ends before a completion event without content |
| `stream_retry_delay`        | `0.5`                  | Seconds to wait between stream retries                                  |
| `system_prompt`             | `""`                   | Optional system prompt, injected for every front-end (REPL, `run`, `serve`) |
| `temperature`               | `0.7`                  | Sampling temperature                                                   |
| `tool_analysis`             | `false`                | Model-generated one-line analysis of each tool result (log-only)      |
| `tool_calling`              | `true`                 | Enable OpenAI-compatible function calling                              |
| `tool_max_result_chars`     | `100000`               | Cap tool-result content returned to the model (`... (truncated)` appended). `0` = unlimited. With the default, the model sizes files via the `file_read` header and pages with `offset`/`limit` |
| `tool_permission`           | *(see below)*          | Category permission actions                                            |
| `tool_status_visible`       | `true`                 | Show dimmed tool status in the REPL                                    |
| `tools.allow`               | `[]`                   | Name-level allowlist. Empty means no restriction                       |
| `tools.deny`                | `[]`                   | Name-level deny list (takes precedence over allow)                     |
| `unattended`                | `false`                | Unattended mode: no stdin is read at any depth. Confirms auto-deny and `ask target='human'` parks as a pending request (`.replio/asks.json`) instead of prompting. See [Unattended mode](#unattended-mode) |
| `web_search`                | `false`                | Auto-search mode: search the web before answering                       |
| `word_streaming`            | `true`                 | Buffer REPL output to word boundaries so words render fully formed (no mid-word pauses). `false` streams character-by-character |

### `modes`

Modes are named postures combining an instruction block with tool-policy overrides. The built-ins ship as defaults - `build` (no overrides) and `plan` (read-only, `edit` and `bash` denied):

```json
{
  "mode": "plan",
  "modes": {
    "build": { "system_prompt": "", "tool_permission": {} },
    "plan": {
      "system_prompt": "You are in plan mode (read-only)...",
      "tool_permission": { "edit": "deny", "bash": "deny" }
    }
  }
}
```

Each mode may define `system_prompt` (instructions), `tool_permission` (category actions merged over the base, mode wins per key), `tools.deny` (appended to the base deny list), and `tools.allow` (replaces the base allowlist when non-empty). An unknown `mode` falls back to `build`. Switch live with `/mode <name>` or `--mode <name>` on `replio run` / `replio serve`. The mode instruction and `system_prompt` are injected as a system message for every front-end, and the active mode is recorded on each assistant message in the session log.

### `tool_permission`

```json
{
  "ask": "allow",
  "bash": "ask",
  "bash_allow": ["pytest", "python -m unittest", "ruff", "git"],
  "catalog": "allow",
  "delegate": "allow",
  "edit": "allow",
  "list": "allow",
  "mcp": "ask",
  "read": "allow",
  "team": "allow",
  "web": "allow"
}
```

Actions are `allow` (no prompt), `ask` (y/N confirm), `deny` (tool hidden/refused). Read/write/list outside the worktree escalate to `ask` automatically. The `delegate` category gates the `delegate` tool. On top of the category action, delegation resolves its permission from the target type - a configured type uses its own `tool_permission` overrides (category `delegate` defaulting to `allow`), while an agent type not in the registry defaults to `deny` (see [types.md](types.md)). The `team` category gates the `team` tool (default `allow`), separate from `delegate` so a type can be a delegation target yet be barred from running pipelines. The `ask` category gates the `ask` tool (default `allow` - the interaction itself, answered by the human or the lead agent, see [tools.md](tools.md)). The `catalog` category gates the `catalog` tool (default `allow`) - it writes only to the project catalog in `.replio/`, so a team-composing agent can manage types, teams, and skills without general file edits. Set it to `ask` to confirm every catalog change.

### `ask_policy`

Routes the `ask` tool by kind:

```json
{
  "ask_policy": {
    "permission": "auto",
    "direction": "human"
  }
}
```

- `permission` - a sub-agent's request for a tool or category it is not allowed to use (`ask(kind="permission", permission="bash")`). `auto` has the lead agent decide and grants one use, `human` routes to the operator, `deny` disables grants. A request above the engine's `grant_permission` ceiling is always denied. The operator may grant `always` (reusable for the rest of that sub-agent's run), the lead only ever grants `once`.
- `direction` - a decision or scope change. `human` (default) routes to the operator, `auto` to the lead.

### Permission authority

Every engine has two permission axes:

- `tool_permission` - what the engine itself may use.
- `grant_permission` - the ceiling on what it may hand down to sub-agents.

A sub-agent's effective permissions are the parent's `tool_permission`, narrowed by the type's `tool_permission` carve and capped by the parent's `grant_permission`. A type can never widen a category above the ceiling, so a sub-agent cannot gain a permission its caller was not authorized to delegate. `grant_permission` defaults to the engine's own `tool_permission`, so delegation never escalates unless a type (or config) explicitly widens the ceiling.

A type that sets `grant_permission` may delegate categories it does not use itself - e.g. a supervisor with `edit`/`bash` denied for itself but allowed in its ceiling can hand them to an `implementer` while never running them.

An approved permission request creates a one-shot grant on the asking sub-agent (`once`), consumed by the next matching call. The operator may grant `always`, reusable for the rest of that sub-agent's run. Grants are never inherited by grandchildren and are recorded in the session `permissions` audit array.

### Unattended mode

`unattended: true` guarantees that nothing in a turn reads stdin, at any depth - an overnight REPL run cannot freeze on a prompt. It applies to the whole sub-agent tree:

- **Confirms auto-deny.** A tool whose policy action is `ask` (e.g. `run_command` with `bash: ask`) returns `[cancelled] User declined the <name> call` instead of prompting.
- **`ask target='human'` parks instead of prompting.** The root engine drops its terminal UI (`_ask_ui` is not propagated down the tree), and any human-routed ask becomes a pending request persisted in `.replio/asks.json`, returned to the agent as `[parked] Ask #<id> ...` so it continues or finishes. A sub-agent's human ask parks rather than falling back to its lead - the operator should decide. Permission asks routed `human` park the same way. Routed `auto` still go to the lead (a one-shot grant).
- **Model approval is not prompted.** An unapproved type/team model is denied (the run reports the error) unless the headless `approve_models` flag was passed - launch with `--approve-model` if the run needs to approve one itself.

Enable it per run with `replio --unattended` (not persisted), in config with `unattended: true`, or live with `/unattended`. Parked asks are listed and answered with `/asks` or the serve API (`GET /asks`, `POST /asks/<id>/answer`). Answering marks the ask answered and injects the answer into the origin session, so the next turn on that session resumes with the operator's decision in context. Scheduled/durable job engines run unattended, so a job parks its human asks the same way. `confirm_timeout` (seconds, default `0` = forever) additionally makes attended confirm/ask prompts self-limiting, so a prompt left unanswered auto-denies instead of hanging.

### `bash_allow` - command allowlist for `run_command`

`tool_permission.bash_allow` (list, default `[]`) restricts `run_command` to commands whose first token matches an allowed prefix. Empty or unset means unrestricted (the `bash` action applies to every command). When set:

- Commands split into chained segments over `&&`, `||`, `;`, `|`, and `&`. Every segment must start with an allowed prefix (e.g. `pytest -q && ruff check .` needs both `pytest` and `ruff`).
- Shell-script forms are rejected outright: multi-line commands and heredocs (`<<`) always return `deny`.
- A matching command falls through to the normal `bash` action (`ask` by default, `allow`/`deny` per config). A non-matching command is `deny`.

The check runs through the per-invocation policy resolver, so it composes with modes, name-level `tools.deny`/`tools.allow`, and the worktree escalation. `bash_allow` gives a coding agent a safe default set (tests, linters, git) without opening up arbitrary shell.

## Model registry (not config)

Two global files live separately from config in `~/.config/replio/`. Neither is part of the config merge - `/config` never lists or writes them, and neither has a local scope.

### Provider registry (`providers.json`)

`~/.config/replio/providers.json` (written `0600` when it holds keys) stores the active connections, keyed by provider name:

```json
{
  "ollama": {
    "base_url": "https://custom.example/v1",
    "api_key": "...",
    "added_at": "...",
    "last_used": "..."
  }
}
```

- `api_key` lives here, one per provider - the only place API keys live.
- `base_url` is the effective base URL of the connection - the preset provider default (e.g. `/connect ollama`) or a custom URL (`/connect <url>`). The engine falls back to it when the config leaves `base_url` empty.
- Managed through `/connect` (writes the key and any custom base URL). Re-running it re-enters a missing or stale key.
- The engine resolves the active provider's API key from this file (matching entry or `""`), falling back to a stored custom `base_url` when the config has none. There is no `api_key` config key anymore - `replio config set api_key` would store an unused ordinary value. Deleting a project config cannot lose the registry - it is global by design.

### Model registry (`models.json`)

`~/.config/replio/models.json` is the history of approved models - entries `{provider, model, added_at, last_used}`, no API keys (those live in `providers.json`). It records every model you connect or switch to, so `/models` shows what has been used per provider with `>` marking the active one. The active model still comes from `config.model`.

- `/connect` records the model for the connection it just saved.
- `/models` shows approved models grouped by provider, the active one marked `>`, plus `(key)` when that provider has a stored key.
- `/models list [provider]` probes a provider's advertised models live (default: current provider).
