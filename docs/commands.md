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
| `/connect`              |                | Interactive provider connection setup                          |
| `/config`               |                | Show, get, or set config values (`/config <key> <value>`)      |
| `/session`              |                | Manage sessions: `new`, `list`, `preview`, `load`, `delete`, `save` |
| `/compact`              | `/c`           | Summarize the conversation and trim the provider context       |
| `/tool`                 |                | Run a tool directly (`/tool <name> {"key": "value"}`)          |
| `/plugins`              | `/plugin`      | Manage plugins: `list`, `enable`, `disable`, `install`, `update`, `uninstall` |

## CLI

```
usage: replio [-h] [--path PATH] [-v] {run,serve,plugins} ...
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
| `--output`           | `json` (default) or `text`                                   |
| `--verbose`          | Print tool status and diagnostics to stderr                   |
| `--session-id`       | Persistent session name (load or create)                     |
| `--yes`              | Auto-approve tools that require confirmation                 |
| `--no`               | Auto-deny tools that require confirmation (default)          |
| `--path`             | Project path                                                 |

### `replio serve`

HTTP JSON API server. See [api.md](api.md).

| Flag          | Default      | Description                  |
|---------------|--------------|------------------------------|
| `--host`      | `127.0.0.1`  | Bind address                 |
| `--port`      | `8787`       | Bind port                    |
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
