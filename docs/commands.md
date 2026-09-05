# Commands & CLI

## Slash commands

Run `replio` and type `/` - commands tab-complete. Use `/help` or `/help <cmd>` for details.

| Command                 | Aliases        | Description                                                    |
|-------------------------|----------------|----------------------------------------------------------------|
| `/help`                 | `/h`           | Show available commands and tools (`/help <cmd|tool>` for detail) |
| `/exit`                 | `/quit`, `/q`  | Save and exit                                                  |
| `/version`              | `/v`           | Show the Replio version                                       |
| `/model`                 |                | Show or switch the active model. `model list` shows the approved-model history grouped by provider (with `(key)` when the provider has a stored key), `model list --online [provider]` probes a provider's available models. `model <provider>/<model>` switches provider and model together, approving the model on confirm |
| `/models`                | `/model-list` | List models available from the connected provider              |
| `/provider`              |                | Show or switch the active provider                             |
| `/mode`                 |                | Show or switch the agent mode (`/mode plan` = read-only, `/mode build`, or a custom mode) |
| `/connect`              |                | Connect a provider. `/connect` picks from the known providers interactively; `/connect <name>` presets a known provider's defaults and (re)enters its API key; `/connect <url>` detects a known host or creates a named custom provider (derived from the host, or `/connect <url> <name>` to name it). Tests the connection before saving, stores the API key + base URL in the global `providers.json`, and writes `provider`/`base_url` into config - the model is picked separately with `/model` |
| `/config`               |                | Show, get, set, or unset config values (`/config <key> <value>`, `/config unset <key>`, `/config --global <key> <value>` for a global line). The listing appends each key's origin: `(default)`, `(global)`, or `(local)` |
| `/session`              |                | Manage sessions: `new`, `list`, `preview`, `load`, `delete`, `save`, `export` |
| `/compact`              | `/c`           | Summarize the conversation and trim the provider context       |
| `/type`              |                | Manage types: `list` (`list <tag>` filters), `show <name>`, `new <name> [prompt]`, `remove <name>`. See [types.md](types.md) |
| `/tool`                 |                | Run a tool directly (`/tool <name> {"key": "value"}`)          |
| `/jobs`                 |                | Manage scheduled and durable jobs: `list`, `status`, `show`, `add`, `approve`, `reject`, `enable`, `disable`, `stop`, `remove`, `run`. See [jobs.md](jobs.md) |
| `/plugins`              | `/plugin`      | Manage plugins: `list`, `enable`, `disable`, `install`, `update`, `uninstall` |

`/help` renders commands with their subcommands indented below, and lists the allowed tools (policy- and mode-filtered, so plan mode hides write and exec tools) the same way under `/tool`. `/tool` with no arguments lists the same tools with their short descriptions.

`/session export <name> [out]` renders a saved session as Markdown (see [session.md](session.md)).

Delegation is a normal tool: the lead agent proposes it, or you run it directly - `/tool delegate {"type": "researcher", "task": "..."}` routes through the same tool policy. A configured type delegates without prompting (`delegate` category defaults to `allow`, set an agent type's `delegate` to `ask` to confirm), and an agent type outside the registry is denied. See [types.md](types.md) and [swarm.md](swarm.md).

## CLI

```
usage: replio [-h] [--path PATH] [-v] {run,export,models,eval,serve,mcp,config,plugins,jobs,fleet} ...
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
| `--model`            | Model override (accepts a `provider/model` ref; an explicit `--model` auto-approves) |
| `--approve-model`    | Approve the configured model ref without prompting             |
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

### `replio models`

List the models the connected provider advertises.

| Flag             | Default                      | Description                       |
|------------------|------------------------------|-----------------------------------|
| `--path`         |                              | Project path                      |

### `replio eval`

Tool-use evaluation harness - run task fixtures through the agent loop and report metrics. See [eval.md](eval.md).

```bash
replio eval --path <project> list              # list discovered fixtures
replio eval --path <project> run [--fixture <id>] [--provider P] [--model M]
replio eval --path <project> run --compare ollama,openai --output json
```

| Flag             | Default                      | Description                       |
|------------------|------------------------------|-----------------------------------|
| `--fixture`      |                              | Fixture id or substring (default: all) |
| `--provider`     |                              | Provider override                 |
| `--model`        |                              | Model override                    |
| `--base-url`     |                              | Base URL override                 |
| `--compare`      |                              | Comma-separated providers to compare |
| `--output`       | `table`                      | `table` or `json`                 |

### `replio config`

Scoped, scriptable config management (same layers as `/config` - see [config.md](config.md)).

```bash
replio config get [key ...] [--show-origin]   # effective values, default all keys
replio config set <key> <value> [--global]    # JSON-parseable value, default local
replio config unset <key> [--global]          # drop a value from the selected scope
```

| Flag             | Default                      | Description                       |
|------------------|------------------------------|-----------------------------------|
| `--global`       |                              | Operate on `~/.config/replio/config.json` |
| `--local`        | (default)                    | Operate on the project `.replio/config.json` |
| `--path`         |                              | Project path                      |
| `--show-origin`  |                              | `get` only - append default/global/local |

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

### `replio jobs`

Scheduled and durable jobs (cron / interval / one-shot), with retries, backoff, a human-in-the-loop approval gate, and a recorded run history. See [jobs.md](jobs.md).

| Subcommand    | Description                                                              |
|---------------|--------------------------------------------------------------------------|
| `list`        | Table of jobs: schedule, status, next and last run                       |
| `status`      | Runtime summary per job: fired count, last error, uptime, approval state |
| `show`        | `replio jobs show <name>` - definition plus full run history + last output|
| `add`         | `replio jobs add <name> --file jobs/<name>.md --cron "0 2 * * *"` (or `--interval N` / `--at ISO`, `--prompt` optional when `--file` is given), plus `--mode`, `--provider`/`--model`, `--type`, `--system-prompt`, `--tools-deny`, `--tool-permission`, `--retries`, `--backoff`, `--timeout`, `--require-approval`, `--approve-model`, `--approval auto` |
| `approve`     | `approve <name>` - activate a job (or arm the next run for `--require-approval` jobs) |
| `reject`      | `reject <name>` - send back to proposed and disable                       |
| `enable` / `disable` / `stop` | Toggle the enabled gate (`stop` = `disable`)                     |
| `edit`        | `edit <name>` - open the job's linked task file in `$EDITOR` (creates the template first) |
| `remove`      | `remove <name>` - drop the definition (sessions are kept)                 |
| `run`         | `run <name> [--no-retry] [--verbose]` - run now, apply retries, print the answer. `--verbose` streams the live turn. Exit `0` verified / `1` failed |
| `daemon`      | `daemon [--tick 15] [--quiet]` - scheduler loop, Ctrl-C to stop           |

### `replio fleet`

Supervise a fleet of scoped `replio serve` agents: ports, health checks, restart policy, config generation. See [fleet.md](fleet.md).

| Subcommand    | Description                                                                     |
|---------------|---------------------------------------------------------------------------------|
| `init`        | Scan immediate subdirectories holding `.replio/config.json` into the manifest    |
| `add`         | `add <name> [--dir] [--port N] [--max-restarts N]` - add an agent                |
| `remove`      | `remove <name>` - remove an agent (stops it if running)                          |
| `up`          | `up [--detach]` - start agents. Ctrl-C = graceful down, `--detach` = background daemon |
| `down`        | Stop the supervised agents and the daemon if running                             |
| `status`      | Live table: agent, enabled, port, pid, state, restarts, last error               |
| `restart`     | `restart [name|all]` - stop, reset restart backoff, relaunch (default: all)     |
| `logs`        | `logs <name> [n] [--follow]` - tail an agent's `.replio/logs/<name>.log`         |
| `config`      | `config <name> --provider/--model/--type/--system-prompt/--mode/--tools-deny/--tool-permission` - write only those keys into `<dir>/.replio/config.json` |

`--path` may be given either before the subcommand (`replio --path X fleet status`) or after it (`replio fleet --path X status`).

### `replio plugins`

Manage plugins headlessly. See [plugins.md](plugins.md).

| Subcommand    | Description                                                     |
|---------------|-----------------------------------------------------------------|
| `list`        | List installed plugins and their load status                    |
| `install`     | `replio plugins install <git-url|path> [--global] [--deps]` - install a plugin |
| `update`      | `replio plugins update <name>` - re-fetch from the recorded source |
| `uninstall`   | `replio plugins uninstall <name>` - remove a plugin             |

`--path` may be given either before the subcommand (`replio --path X plugins list`) or after it (`replio plugins --path X list`).
