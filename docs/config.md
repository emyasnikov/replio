# Configuration

Config is a single JSON object read from two files, merged per key with project-local values winning:

1. **Global** - `~/.config/replio/config.json` (user-wide defaults, credentials).
2. **Local** - `.replio/config.json` in the project path (project overrides).

Every process merges them in memory. Nothing is ever distributed to folders. Writes default to the **local** file and hold only the keys you actually selected - a save never re-writes the merged config. `api_key` is special-cased and always stored in the **global** file (written with `0600` perms), never in a project file. Loading a config that has a local `api_key` moves it to the global file and drops it locally.

```bash
# inspect in the REPL (origin: default/global/local)
/config
# set a value (project-local)
/config temperature 0.3
# set a structured value
/config tools.deny ["run_command", "web_search"]
# remove a project-local value, falling back to global/default
/config unset temperature
# reload from disk
/config reload
```

The `replio config` CLI does the same headlessly and is fully scriptable:

```bash
replio config get max_tokens --show-origin     # one or more values + where they come from
replio config set max_tokens 0                 # project-local
replio config set max_tokens 0 --global        # global file
replio config unset max_tokens                 # remove from project-local
replio config set api_key ...                  # always global, never local
```

## Schema

| Key                         | Default                | Description                                                            |
|-----------------------------|------------------------|------------------------------------------------------------------------|
| `provider`                  | `"ollama"`             | Provider name (`ollama`, `openai`, `groq`, `anthropic`, `openai-compatible`) |
| `model`                     | `"llama3.2"`           | Model name                                                             |
| `base_url`                  | `"https://api.ollama.com"` | Provider endpoint                                                  |
| `api_key`                   | `""`                   | Provider API key                                                       |
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
| `tool_analysis`             | `false`                | Model-generated one-line analysis of each tool result (log-only)      |
| `session_tool_max_chars`    | `0`                    | `0` = unlimited. Caps persisted tool-result content                    |
| `tool_max_result_chars`     | `0`                    | `0` = unlimited. Caps tool-result content returned to the model (`... (truncated)` appended). With the default, the model sizes files via the `read_file` header and pages with `offset`/`limit` |
| `query_refine`              | `false`                | Auto-refine short web-search queries via a lightweight model call      |
| `query_refine_min_words`    | `3`                    | Minimum query length before refinement applies                         |
| `query_refine_context`      | `4`                    | Recent-message context to inject into refinement                       |
| `show_thinking`             | `false`                | Stream thinking/reasoning tokens dimmed. When off, thinking is shown only as an animated spinner plus a `+ Thought N.Ns` summary (display only - does not change what is sent to the model) |
| `reasoning`                 | `"auto"`               | Request reasoning from the model and control its token budget: `false`/`"off"` = do not request, `true`/`"on"`/`"auto"` = request with provider default, `"low"`/`"medium"`/`"high"` = explicit budget hint. Mapping is provider-specific (OpenAI `reasoning_effort`, Claude `thinking.budget_tokens`, Qwen `enable_thinking`) |
| `markdown_streaming`        | `false`                | Basic markdown-aware streaming                                         |
| `word_streaming`            | `true`                 | Buffer REPL output to word boundaries so words render fully formed (no mid-word pauses). `false` streams character-by-character |
| `show_context_size`         | `true`                 | Dimmed context-size line after each response                           |
| `clear_screen`              | `true`                 | Clear the screen before the REPL banner                                |
| `show_version`              | `true`                 | Show the version in the REPL banner                                    |
| `compact_keep`              | `4`                    | Messages to keep when compacting the provider context                  |
| `noise_tools`               | `["fetch_page"]`       | Tool results replaced by a marker in persisted sessions                |
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
  "edit": "allow",
  "list": "allow",
  "mcp": "ask",
  "read": "allow",
  "web": "allow"
}
```

Actions are `allow` (no prompt), `ask` (y/N confirm), `deny` (tool hidden/refused). Read/write/list outside the project worktree escalate to `ask` automatically.
