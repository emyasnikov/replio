# Commands & CLI

## Slash commands

Run `replio` and type `/` - commands tab-complete. Use `/help` or `/help <cmd>` for details.

| Command                 | Aliases        | Description                                                    |
|-------------------------|----------------|----------------------------------------------------------------|
| `/compact`              | `/c`           | Summarize the conversation and trim the provider context       |
| `/config`              |                | Show, get, set, or unset config values (`/config <key> <value>`, `/config unset <key>`, `/config --global <key> <value>` for a global line). The listing appends each key's origin: `(default)`, `(global)`, or `(local)` |
| `/connect`              |                | Connect a provider. `/connect` picks interactively from the known providers. `/connect <name>` presets a known provider's defaults and (re)enters its API key. `/connect <url>` detects a known host or creates a named custom provider (derived from the host, or `/connect <url> <name>` to name it). Tests the connection before saving, stores the API key + base URL in global `providers.json`, and writes `provider`/`base_url` into config - the model is picked separately with `/model` |
| `/exit`                 | `/quit`, `/q`  | Save and exit                                                  |
| `/help`                 | `/h`           | Show available commands and tools (`/help <cmd|tool>` for detail) |
| `/jobs`                 |                | Manage scheduled and durable jobs: `list`, `status`, `show`, `add`, `approve`, `reject`, `enable`, `disable`, `stop`, `remove`, `run`. See [jobs.md](jobs.md) |
| `/mode`                 |                | Show or switch the agent mode (`/mode plan` = read-only, `/mode build`, or a custom mode) |
| `/model`                 |                | Show or switch the active model. `/model <name>` sets it on the current provider. `/model <provider>/<model>` switches provider and model together, approving the model on confirm |
| `/models`                |                | List configured models, or probe a provider's available models. `/models` shows the approved-model history grouped by provider (`(key)` when the provider has a stored key). `/models list [provider]` probes a provider's advertised models live (default: current provider) |
| `/plugins`              | `/plugin`      | Manage plugins: `list`, `enable`, `disable`, `install`, `update`, `uninstall` |
| `/provider`              |                | Show or switch the active provider                             |
| `/session`              |                | Show or switch the active session: `/session new`, `/session load <name>`, `/session save`. Saved-session catalog operations live under `/sessions` |
| `/sessions`             |                | Manage the saved-session catalog: `list`, `preview`, `delete`, `export <name> [out]` (Markdown output, see [session.md](session.md)) |
| `/skills`               |                | Manage skills: `list`, `show <name>`, `new <name>`, `remove <name>`. See [skills.md](skills.md) |
| `/teams`                |                | Manage teams: `list` (`list <tag>` filters), `show <name>`, `new <name> [description]`, `remove <name>`, `run <name> <task>`. See [teams.md](teams.md) |
| `/thinking`             | `/reasoning`   | Show or switch reasoning display and request (`/thinking on` streams reasoning dimmed, `off` shows only a spinner) |
| `/tool`                 |                | Run a tool directly (`/tool <name> {"key": "value"}`)          |
| `/types`                |                | Manage types: `list` (`list <tag>` filters), `show <name>`, `new <name> [prompt]`, `remove <name>`. See [types.md](types.md) |
| `/unattended`           |                | Show or toggle unattended mode (`/unattended on`/`off`): no stdin at any depth, confirms auto-deny, human asks route to the lead or return without pausing. See [config.md](config.md#unattended-mode) |
| `/version`              | `/v`           | Show the Replio version                                       |

`/help` renders commands with subcommands indented below and lists the allowed tools (policy- and mode-filtered, so plan mode hides write and exec tools) the same way under `/tool`. `/tool` with no arguments lists the same tools with their short descriptions.

Delegation is a normal tool: the lead agent proposes it, or you run it directly - `/tool delegate {"type": "researcher", "task": "..."}` routes through the same tool policy. A configured type delegates without prompting (`delegate` defaults to `allow`. Set an agent type's `delegate` to `ask` to confirm), and an agent type outside the registry is denied. See [types.md](types.md) and [swarm.md](swarm.md).

## CLI

```
usage: replio [-h] [--path PATH] [-v] {config,eval,export,fleet,jobs,mcp,models,plugins,run,serve} ...
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
| `--model`            | Model override (accepts a `provider/model` ref. Explicit `--model` auto-approves) |
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

List configured models, or probe a provider's available models (mirrors `/models`).

```bash
replio models                          # approved-model history grouped by provider, `>` marks the active model, `(key)` a stored key
replio models list [provider]          # probe a provider's advertised models (default: current), exit 1 on failure
```

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
replio config reload                          # re-read the config files from disk
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

Scheduled and durable jobs (cron / interval / one-shot), with retries, backoff, a human-in-the-loop approval gate, and recorded run history. See [jobs.md](jobs.md).

| Subcommand    | Description                                                              |
|---------------|--------------------------------------------------------------------------|
| `add`         | `replio jobs add <name> --file jobs/<name>.md --cron "0 2 * * *"` (or `--interval N` / `--at ISO`, with `--prompt` optional when `--file` given), plus `--mode`, `--provider`/`--model`, `--type`, `--system-prompt`, `--tools-deny`, `--tool-permission`, `--retries`, `--backoff`, `--timeout`, `--require-approval`, `--approve-model`, `--approval auto` |
| `approve`     | `approve <name>` - activate a job (or arm the next run for `--require-approval` jobs) |
| `daemon`      | `daemon [--tick 15] [--quiet]` - scheduler loop, Ctrl-C to stop           |
| `edit`        | `edit <name>` - open the job's linked task file in `$EDITOR` (creates the template first) |
| `enable` / `disable` / `stop` | Toggle the enabled gate (`stop` = `disable`)                     |
| `list`        | Table of jobs: schedule, status, next and last run                       |
| `reject`      | `reject <name>` - send back to proposed and disable                       |
| `remove`      | `remove <name>` - drop the definition (sessions are kept)                 |
| `run`         | `run <name> [--no-retry] [--verbose]` - run now, apply retries, print the answer. `--verbose` streams the live turn. Exit `0` verified / `1` failed |
| `show`        | `replio jobs show <name>` - definition plus full run history + last output|
| `status`      | Runtime summary per job: fired count, last error, uptime, approval state |

### `replio fleet`

Supervise a fleet of scoped `replio serve` agents: ports, health checks, restart policy, config generation. See [fleet.md](fleet.md).

| Subcommand    | Description                                                                     |
|---------------|---------------------------------------------------------------------------------|
| `add`         | `add <name> [--dir] [--port N] [--max-restarts N]` - add an agent                |
| `config`      | `config <name> --provider/--model/--type/--system-prompt/--mode/--tools-deny/--tool-permission` - write only those keys into `<dir>/.replio/config.json` |
| `down`        | Stop the supervised agents and the daemon if running                             |
| `init`        | Scan immediate subdirectories holding `.replio/config.json` into the manifest    |
| `logs`        | `logs <name> [n] [--follow]` - tail an agent's `.replio/logs/<name>.log`         |
| `remove`      | `remove <name>` - remove an agent (stops it if running)                          |
| `restart`     | `restart [name|all]` - stop, reset restart backoff, relaunch (default: all)     |
| `status`      | Live table: agent, enabled, port, pid, state, restarts, last error               |
| `up`          | `up [--detach]` - start agents. Ctrl-C = graceful down, `--detach` = background daemon |

`--path` may be given before the subcommand (`replio --path X fleet status`) or after it (`replio fleet --path X status`).

### `replio plugins`

Manage plugins headlessly. See [plugins.md](plugins.md).

| Subcommand    | Description                                                     |
|---------------|-----------------------------------------------------------------|
| `disable`     | `replio plugins disable <name>` - remove a plugin from the plugins list (applies on next start) |
| `enable`      | `replio plugins enable <name>` - add a plugin to the plugins list (applies on next start) |
| `install`     | `replio plugins install <git-url\|path> [--global] [--deps]` - install a plugin |
| `list`        | List installed plugins and their load status                    |
| `uninstall`   | `replio plugins uninstall <name>` - remove a plugin             |
| `update`      | `replio plugins update <name>` - re-fetch from the recorded source |

`--path` may be given before the subcommand (`replio --path X plugins list`) or after it (`replio plugins --path X list`).
