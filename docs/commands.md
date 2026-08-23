# Commands & CLI

## Slash commands

Run `replio` and type `/` - commands tab-complete. Use `/help` or `/help <cmd>` for details.

| Command                 | Aliases        | Description                                                    |
|-------------------------|----------------|----------------------------------------------------------------|
| `/help`                 | `/h`           | Show available commands and tools (`/help <cmd|tool>` for detail) |
| `/exit`                 | `/quit`, `/q`  | Save and exit                                                  |
| `/version`              | `/v`           | Show the Replio version                                       |
| `/model`                |                | Show or switch the active model (`/model gpt-4o`)              |
| `/provider`             |                | Show or switch the active provider                             |
| `/mode`                 |                | Show or switch the agent mode (`/mode plan` = read-only, `/mode build`, or a custom mode) |
| `/connect`              |                | Interactive provider connection setup (tests the connection before saving) |
| `/config`               |                | Show, get, or set config values (`/config <key> <value>`)      |
| `/session`              |                | Manage sessions: `new`, `list`, `preview`, `load`, `delete`, `save`, `export` |
| `/compact`              | `/c`           | Summarize the conversation and trim the provider context       |
| `/tool`                 |                | Run a tool directly (`/tool <name> {"key": "value"}`)          |
| `/plugins`              | `/plugin`      | Manage plugins: `list`, `enable`, `disable`, `install`, `update`, `uninstall` |

`/help` renders commands with their subcommands indented below, and lists the allowed tools (policy- and mode-filtered, so plan mode hides write and exec tools) the same way under `/tool`. `/tool` with no arguments lists the same tools with their short descriptions.

`/session export <name> [out]` renders a saved session as Markdown (see [session.md](session.md)).

## CLI

```
usage: replio [-h] [--path PATH] [-v] {run,export,serve,mcp,plugins} ...
```

Global:

| Flag          | Description                                      |
|---------------|--------------------------------------------------|
| `--path`      | Project path (default: current directory)        |
| `--version`, `-v` | Print the installed version and exit         |

### `replio run`

One-shot headless chat.

| Flag                 | Description                                                  |
|----------------------|--------------------------------------------------------------|
| `--prompt`, `-p`     | **Required.** The prompt to send                              |
| `--provider`         | Provider override (e.g. `ollama`, `openai`, `groq`)           |
| `--model`            | Model override                                               |
| `--base-url`         | Base URL override                                            |
| `--mode`             | Agent mode override (`plan`, `build`, or a custom mode)      |
| `--output`           | `json` (default) or `text`                                   |
| `--verbose`          | Print tool status and diagnostics to stderr                   |
| `--session-id`       | Persistent session name (load or create)                     |
| `--yes`              | Auto-approve tools that require confirmation                 |
| `--no`               | Auto-deny tools that require confirmation (default)          |
| `--path`             | Project path                                                 |

### `replio export`

Export a saved session to Markdown (see [session.md](session.md)).

| Flag             | Default                      | Description                       |
|------------------|------------------------------|-----------------------------------|
| `name`           | **Required**                 | Session name to export            |
| `--out`          | `.replio/exports/<name>.md`  | Output file, `-` for stdout       |
| `--path`         |                              | Project path                      |

### `replio serve`

HTTP JSON API server. See [api.md](api.md). Also serves `POST /mcp` (MCP server) when the `replio-core-mcp` plugin is loaded.

| Flag          | Default      | Description                  |
|---------------|--------------|------------------------------|
| `--host`      | `127.0.0.1`  | Bind address                 |
| `--port`      | `8787`       | Bind port                    |
| `--path`      |              | Project path                 |
| `--mode`      |              | Agent mode override (`plan`, `build`, or a custom mode) |

### `replio mcp`

Run replio as an MCP server over stdio (newline-delimited JSON-RPC). See [mcp.md](mcp.md). Requires the `replio-core-mcp` plugin.

| Flag          | Default      | Description                  |
|---------------|--------------|------------------------------|
| `--path`      |              | Project path                 |

### `replio plugins`

Manage plugins headlessly. See [plugins.md](plugins.md).

| Subcommand    | Description                                                     |
|---------------|-----------------------------------------------------------------|
| `list`        | List installed plugins and their load status                    |
| `install`     | `replio plugins install <git-url|path> [--global] [--deps]` - install a plugin |
| `update`      | `replio plugins update <name>` - re-fetch from the recorded source |
| `uninstall`   | `replio plugins uninstall <name>` - remove a plugin             |

`--path` may be given either before the subcommand (`replio --path X plugins list`) or after it (`replio plugins --path X list`).
