# Configuration

Config is a single JSON object. Global config lives at `~/.config/replio/config.json`; a local config at `.replio/config.json` (in the project path) merges on top, and local values win.

```bash
# inspect in the REPL
/config
# set a value
/config temperature 0.3
# set a structured value
/config tools.deny ["run_command", "web_search"]
# reload from disk
/config reload
```

## Schema

| Key                         | Default                | Description                                                            |
|-----------------------------|------------------------|------------------------------------------------------------------------|
| `provider`                  | `"ollama"`             | Provider name (`ollama`, `openai`, `groq`, `anthropic`, `openai-compatible`) |
| `model`                     | `"llama3.2"`           | Model name                                                             |
| `base_url`                  | `"https://api.ollama.com"` | Provider endpoint                                                  |
| `api_key`                   | `""`                   | Provider API key                                                       |
| `temperature`               | `0.7`                  | Sampling temperature                                                   |
| `max_tokens`                | `0`                    | `0` = unset (provider default); positive value caps output             |
| `system_prompt`             | `""`                   | Optional system prompt                                                 |
| `tool_calling`              | `true`                 | Enable OpenAI-compatible function calling                              |
| `tool_status_visible`       | `true`                 | Show dimmed tool status in the REPL                                    |
| `tool_analysis`             | `false`                | Model-generated one-line analysis of each tool result (log-only)      |
| `session_tool_max_chars`    | `0`                    | `0` = unlimited; caps persisted tool-result content                    |
| `query_refine`              | `false`                | Auto-refine short web-search queries via a lightweight model call      |
| `query_refine_min_words`    | `3`                    | Minimum query length before refinement applies                         |
| `query_refine_context`      | `4`                    | Recent-message context to inject into refinement                       |
| `show_thinking`             | `true`                 | Stream thinking/reasoning tokens dimmed                                |
| `markdown_streaming`        | `false`                | Basic markdown-aware streaming                                         |
| `show_context_size`         | `true`                 | Dimmed context-size line after each response                           |
| `clear_screen`              | `true`                 | Clear the screen before the REPL banner                                |
| `show_version`              | `true`                 | Show the version in the REPL banner                                    |
| `compact_keep`              | `4`                    | Messages to keep when compacting the provider context                  |
| `noise_tools`               | `["fetch_page"]`       | Tool results replaced by a marker in persisted sessions                |
| `web_search`                | `false`                | Auto-search mode: search the web before answering                       |
| `search_results`            | `5`                    | Number of search results to fetch                                      |
| `tools.allow`               | `[]`                   | Name-level allowlist; empty means no restriction                       |
| `tools.deny`                | `[]`                   | Name-level deny list (takes precedence over allow)                     |
| `tool_permission`           | *(see below)*          | Category permission actions                                            |
| `plugins`                   | *(bundled)*            | Plugins to load; empty = all discovered plugins load                   |

### `tool_permission`

```json
{
  "read": "allow",
  "list": "allow",
  "edit": "allow",
  "bash": "ask",
  "web": "allow"
}
```

Actions are `allow` (no prompt), `ask` (y/N confirm), `deny` (tool hidden/refused). Read/write/list outside the project worktree escalate to `ask` automatically.
