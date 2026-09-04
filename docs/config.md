# Configuration

Config is a single JSON object read from two files, merged per key with project-local values winning:

1. **Global** - `~/.config/replio/config.json` (user-wide defaults, credentials).
2. **Local** - `.replio/config.json` in the project path (project overrides).

Every process merges them in memory. Nothing is ever distributed to folders. Writes default to the **local** file and hold only the keys you actually selected - a save never re-writes the merged config. API keys are not part of the config: they live in the global provider registry (`~/.config/replio/providers.json`) and are managed through `/connect` (see [Models](#model-registry-not-config)).

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

Deleting a project's `.replio/config.json` reverts that project to the global and built-in defaults. To keep settings across local deletions, globalize individual lines with `--global` (both the REPL `/config` and the CLI accept it), e.g. `/config --global provider ollama`, `/config --global model <model>`.

## Schema

| Key                         | Default                | Description                                                            |
|-----------------------------|------------------------|------------------------------------------------------------------------|
| `provider`                  | `"ollama"`             | Provider name (`ollama`, `openai`, `groq`, `anthropic`, `opencode`, `opencode-go`, `openai-compatible`) |
| `model`                     | `"llama3.2"`           | Model name                                                             |
| `base_url`                  | `"https://api.ollama.com"` | Provider endpoint                                                  |
| `temperature`               | `0.7`                  | Sampling temperature                                                   |
| `max_tokens`                | `8192`                 | Output token cap sent to the provider. `0` = unset (provider default applies, e.g. Ollama caps at 2048). Default `8192` overrides low provider defaults |
| `stream_retries`            | `2`                    | Extra attempts (after the first) when a provider stream ends before a completion event with no content |
| `stream_retry_delay`        | `0.5`                  | Seconds to wait between stream retries                                  |
| `auto_continue`             | `true`                 | On truncation (`finish_reason=length`) with a partial answer, re-request the turn with a "continue" instruction and stitch the parts into one message |
| `auto_continue_max`         | `2`                    | Max continuation rounds per turn before the truncation is reported     |
| `connect_check`             | `true`                 | Test the provider connection when config changes: `/connect` probes before saving (broken values are rejected unless confirmed), `/provider` warns on a failed probe. `false` skips all probes |
| `system_prompt`             | `""`                   | Optional system prompt, injected for every front-end (REPL, `run`, `serve`) |
| `mode`                      | `"build"`              | Active agent mode (`build`, `plan`, or a custom mode from `modes`) |
| `tool_calling`              | `true`                 | Enable OpenAI-compatible function calling                              |
| `tool_status_visible`       | `true`                 | Show dimmed tool status in the REPL                                    |
| `glyph_lines`               | `true`                 | Typed `<glyph> <verb> <arg>` status lines for mapped categories. When off, or for unmapped categories, the `[tool: arg]` oneliner is used |
| `glyph_params`              | `true`                 | Append the tool call parameters to glyph status lines and confirm prompts (e.g. `← Read engine.py [offset=299, limit=85]`). Off for bare `<glyph> <verb> <arg>` |
| `show_errors`               | `true`                 | Show a dimmed `! Error: ...` line (first line of the result) when a tool call fails. Off hides the line |
| `show_notes`                | `true`                 | Show a dimmed info line for soft tool results (e.g. `(empty file)`, `(no matches for "x")`). Off hides the line |
| `tool_analysis`             | `false`                | Model-generated one-line analysis of each tool result (log-only)      |
| `delegate_echo`             | `true`                 | When the `delegate` tool runs, show the sub-agent's final answer and a sub footer (duration + completion tokens) in the REPL. Off hides the result. The sub footer is emitted alongside the sub-agent's own rendered output only when on |
| `session_tool_max_chars`    | `0`                    | `0` = unlimited. Caps persisted tool-result content                    |
| `tool_max_result_chars`     | `100000`               | Caps tool-result content returned to the model (`... (truncated)` appended). `0` = unlimited. With the default, the model sizes files via the `file_read` header and pages with `offset`/`limit` |
| `list_dir_max_entries`      | `200`                  | Cap the number of entries `list_dir` returns (`... (showing first N of M entries)` appended). `0` = unlimited |
| `query_refine`              | `false`                | Auto-refine short web-search queries via a lightweight model call      |
| `query_refine_min_words`    | `3`                    | Minimum query length before refinement applies                         |
| `query_refine_context`      | `4`                    | Recent-message context to inject into refinement                       |
| `show_thinking`             | `false`                | Stream thinking/reasoning tokens dimmed. When off, thinking is shown only as an animated spinner plus a `+ Thought N.Ns` summary (display only - does not change what is sent to the model) |
| `show_thought_duration`     | `true`                 | When thinking is streamed (`show_thinking` on), print a dimmed `(Thought N.Ns)` line after each thinking block. Off hides it |
| `reasoning`                 | `"auto"`               | Request reasoning from the model and control its token budget: `false`/`"off"` = do not request, `true`/`"on"`/`"auto"` = request with provider default, `"low"`/`"medium"`/`"high"` = explicit budget hint. Mapping is provider-specific (OpenAI `reasoning_effort`, Claude `thinking.budget_tokens`, Qwen `enable_thinking`) |
| `markdown_streaming`        | `false`                | Basic markdown-aware streaming                                         |
| `word_streaming`            | `true`                 | Buffer REPL output to word boundaries so words render fully formed (no mid-word pauses). `false` streams character-by-character |
| `show_context_size`         | `true`                 | Dimmed context-size line after each response                           |
| `footer_tokens`             | `["context"]`          | Which token counts the footer shows, in order, joined by `/`. `context` = `<n> tokens` (context/input size, chars/4 fallback), `in`/`out`/`thinking` = `<n>t` from provider usage (unavailable counts are skipped). Empty list hides the token section entirely |
| `clear_screen`              | `true`                 | Clear the screen before the REPL banner                                |
| `show_version`              | `true`                 | Show the version in the REPL banner                                    |
| `compact_keep`              | `4`                    | Messages to keep when compacting the provider context                  |
| `project_instructions`     | `"AGENTS.md"`          | Per-worktree instructions file auto-loaded into the system prompt (e.g. `AGENTS.md`, `CLAUDE.md`). `""` disables. Absent files are skipped. Content is capped at 20000 chars |
| `noise_tools`               | `["web_fetch", "open", "fetch_page"]` | Tool results replaced by a marker in persisted sessions                |
| `web_search`                | `false`                | Auto-search mode: search the web before answering                       |
| `search_results`            | `5`                    | Number of search results to fetch                                      |
| `tools.allow`               | `[]`                   | Name-level allowlist. Empty means no restriction                       |
| `tools.deny`                | `[]`                   | Name-level deny list (takes precedence over allow)                     |
| `tool_permission`           | *(see below)*          | Category permission actions                                            |
| `mcp.servers`               | `[]`                   | MCP client server definitions (see [mcp.md](mcp.md) for the schema)     |
| `mcp_server.allow_ask`      | `true`                 | When serving MCP, run `ask`-policy tools (deferred to the client) vs refuse them |
| `plugins`                   | *(bundled)*            | Plugins to load. Empty = all discovered plugins load                   |

### `modes`

Modes are named postures combining an instruction block with tool-policy overrides. The built-ins ship as defaults - `build` (no overrides) and `plan` (read-only: `edit` and `bash` categories denied):

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

Each mode may define `system_prompt` (instructions), `tool_permission` (category actions merged over the base `tool_permission`, mode wins per key), `tools.deny` (appended to the base deny list), and `tools.allow` (replaces the base allowlist when non-empty). An unknown `mode` value falls back to `build`. Switch live with `/mode <name>` or set `--mode <name>` on `replio run` / `replio serve`. The mode instruction and `system_prompt` are injected as a system message for every front-end. The active mode is recorded on each assistant message in the session log.

### `tool_permission`

```json
{
  "bash": "ask",
  "bash_allow": ["pytest", "python -m unittest", "ruff", "git"],
  "delegate": "allow",
  "edit": "allow",
  "list": "allow",
  "mcp": "ask",
  "read": "allow",
  "web": "allow"
}
```

Actions are `allow` (no prompt), `ask` (y/N confirm), `deny` (tool hidden/refused). Read/write/list outside the project worktree escalate to `ask` automatically. The `delegate` category gates the `delegate` tool. On top of the category action, delegation resolves its permission from the target type - a configured type uses its own `tool_permission` overrides (category `delegate` defaulting to `allow`), while an agent type not in the registry defaults to `deny` (see [types.md](types.md)).

### `bash_allow` - command allowlist for `run_command`

`tool_permission.bash_allow` (list, default `[]`) restricts `run_command` to commands whose first token matches an allowed prefix. Empty or unset means unrestricted (the `bash` category action applies to every command). When set:

- Each command is split into chained segments over `&&`, `||`, `;`, `|`, and `&`, and every segment must start with one of the allowed prefixes (e.g. `pytest -q && ruff check .` needs both `pytest` and `ruff` allowed).
- Shell-script forms are rejected outright: multi-line commands and heredocs (`<<`) always return `deny`.
- A matching command falls through to the normal `bash` action (`ask` by default, `allow`/`deny` per config). A non-matching command is `deny`.

The check runs through the per-invocation policy resolver, so it composes with modes, name-level `tools.deny`/`tools.allow`, and the worktree escalation. `bash_allow` gives a coding agent a safe default set (tests, linters, git) without opening up arbitrary shell.

## Model registry (not config)

Two global files live separately from config in `~/.config/replio/`. Neither is part of the config merge - `/config` never lists or writes them, and they have no local scope.

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

- `api_key` lives here, one per provider. It is the only place API keys live.
- `base_url` is stored only when it differs from the provider's default; otherwise the provider class default applies.
- Managed through `/connect` (which writes the key and any custom base URL). Re-running `/connect` lets you re-enter a missing or stale key.
- The engine resolves the API key for the active provider from this file (matching entry or `""`), and falls back to a stored custom `base_url` when the config has none. There is no `api_key` config key anymore, and `replio config set api_key` would store an unused ordinary value. Deleting a project config cannot lose the registry - it is global by design.

### Model registry (`models.json`)

`~/.config/replio/models.json` is the history of approved models - entries `{provider, model, added_at, last_used}`, no API keys (keys and custom base URLs live in `providers.json`). It records every model you connect or switch to, so `/model list` shows what has been used per provider and `>` marks the active one. The active model still comes from `config.model`.

- `/connect` records the model for the connection it just saved.
- `/model list` shows the approved models grouped by provider with the active one marked `>`, and `(key)` when that provider has a stored key.
- `/model list --online [provider]` probes a provider's advertised models live (default: current provider).
