# Agent fleets

Replio composes into fleets of single-purpose agents. A documentation agent owns a folder of PDFs. A code agent stays inside one repository. A web-research agent has no filesystem access. Each agent is a full Replio process scoped to a directory. The core is zero-dependency and a process is a few MB, so dozens or hundreds can run on one machine. The thin boundaries of process and permissions keep them apart.

## One agent = one process = one folder

An agent is just `replio serve` pointed at a project directory:

```bash
replio serve --path docs --port 8781 &
replio serve --path src --port 8782 &
```

Each process reads its own `.replio/config.json` (provider, model, system prompt, tool permissions, plugins) and writes its own sessions under `.replio/sessions/`. Nothing is shared at runtime. A crash in one agent cannot take down the others, and configuration drift stays isolated per agent.

## Responsibilities and permissions

Every agent is a single-purpose process. Its responsibility comes from its config, namely which tools are registered. Its permission is enforced by the worktree and tool policy, not by convention.

- **Worktree scoping**: the tool policy treats the launch directory (`--path`, or the current directory) as the worktree. `file_read` / `list_dir` / `file_write` / `glob` / `grep` on a path outside it escalate from `allow` to `ask` (tools/policy.py:35). A doc agent cannot touch files in another agent's folder unless its config says so.
- **Headless auto-deny**: in `serve`/`run` mode, `ask`-gated tools are denied outright (ui.py `HeadlessUI.confirm` answers `auto == 'allow'`). An agent's reachable surface is therefore exactly `allow` tools on paths inside its worktree, plus `--yes` explicit approvals.
- **Tool allow/deny**: `tools.allow` (whitelist mode) and `tools.deny` narrow the registered schema the model sees. A web agent sets `tools.deny: [run_command, file_write]`. A code agent denies `web_search, web_fetch`.
- **Category permissions**: `tool_permission` (`read`/`list`/`edit`/`bash`/`web` > `allow`/`ask`/`deny`) is per-agent. `bash` defaults to `ask` everywhere. Set `tool_permission.bash: allow` only for agents that may run shell commands.
- **Plugins per agent**: the `plugins` config list controls which plugin set loads in each process. Capabilities that need external dependencies (PDF extraction, MCP, vector search) are external plugins. Scoped capabilities (folder watching, text indexing) are bundled ones.

## Example: a documentation agent

A doc agent watches a folder of PDFs, converts new ones to text, indexes them, and answers peers over the API. Decomposed:

| Capability | Home | Dependency |
|---|---|---|
| Folder watching (new-file detection) | internal bundled plugin | stdlib `threading` + `pathlib` |
| Text index over converted files | internal bundled plugin | stdlib |
| PDF > text extraction | external plugin | `pypdf` (lazy import) |
| Vector store / embeddings | external plugin | FAISS/Weaviate (later) |
| MCP server for peer agents | external plugin (planned) | `mcp` (lazy import) |

A minimal agent config (`.replio/config.json` in its own directory):

```json
{
  "provider": "ollama",
  "model": "llama3.2",
  "system_prompt": "You are the documentation agent. Convert PDFs to text, keep the index current, and answer questions from the stored docs.",
  "tools.allow": ["glob", "file_read", "file_write", "run_command", "pdf2text", "watch_folder", "search_index"],
  "tool_permission": { "read": "allow", "list": "allow", "edit": "allow", "bash": "allow", "web": "allow" },
  "plugins": ["replio-core-fs", "replio-core-exec", "replio-core-doc-agent"]
}
```

Launch it, and peers talk to it over the same `POST /chat` API used everywhere:

```bash
replio serve --path agents/docs --port 8781 &
curl localhost:8781/chat -X POST -d '{"prompt": "What does spec-42.pdf say?", "session_id": "docs-pool"}'
```

## Supervisor

`replio fleet` supervises the agents from the terminal: port allocation, health checks, a restart policy, and per-agent config generation. It is the systemd/Compose-shaped layer for a single host, so you do not need Docker to keep agents alive.

A fleet root is a directory holding the agents, typically one folder each. Two files live in the root's `.replio/`:

- `.replio/fleet.json` - the declarative roster. One `AgentDef` per agent: `name`, `dir`, `enabled`, `prefer_port`, `max_restarts` (0 = unlimited), and an optional `command` override (the test seam, real agents use the default `replio serve` command)
- `.replio/fleet.state.json` - runtime state only (pids, ports, status, restart counts, last error). A snapshot the supervisor writes, never edited by hand

Build and run a fleet:

```bash
replio fleet init                    # scan subdirectories holding .replio/config.json
replio fleet config docs-agent --type research-agent    # generate a config
replio fleet add code-agent --dir ../repo --port 8782
replio fleet up                      # foreground, Ctrl-C = graceful down
replio fleet up --detach             # background daemon (replio fleet down stops it)
replio fleet status                  # agent/enabled/port/pid/state/restarts/error table
replio fleet restart code-agent      # stop, reset backoff, relaunch on next sweep
replio fleet logs docs-agent -f      # tail an agent's .replio/logs/<name>.log
```

While `up` is running the supervisor does, every sweep (default 2s):

- **Port allocation** - agents get a free port by bind probe, preferring `prefer_port`, scanning 8780-8890. Edited while running, `add`/`init` take effect on the next sweep
- **Health checks** - a `GET /health` probe (2s timeout). A running agent that fails `unhealthy_threshold` checks (default 2) or whose process exits is treated as a failure
- **Restart policy** - a failed agent is respawned after a backoff that starts at 5s and doubles to a 60s cap. Past `max_restarts` (default 10) the agent goes `crashed` and the supervisor stops touching it until `replio fleet restart <name>` (or `enable`, it resets the counter and re-arms it). Setting `enabled: false` in the manifest stops supervision and the agent
- **Graceful down** - Ctrl-C, `replio fleet down`, or a `SIGTERM` to the detached daemon sends `SIGINT` to each child (the server's own graceful shutdown), then escalates to `SIGKILL` after a grace period

### Per-agent config generation

`replio fleet config <name>` writes only the keys you pass into `<dir>/.replio/config.json`, leaving existing keys intact, so an agent is fired up with its personality before its first launch:

```bash
replio fleet config code-agent \
  --provider ollama --model llama3.2 --mode build \
  --system-prompt "You implement code." \
  --tools-deny web_search \
  --tool-permission "bash=allow" \
  --type programmer
```

`--type` resolves the agent type (bundled + global + local registry) and inlines its `system_prompt`, `model`, and `tool_permission` into the generated keys, so the running agent needs no types registry of its own. An unknown type aborts the write. `--approve-model` pre-approves the model referenced by `--type` or `--model` in the global models registry, so the headless serve agent can use it without prompting.

Agent config is operator-managed: `replio fleet config` is the only intended writer, and a `serve` process has no config-write CLI path today. An engine-level guard making served agents immutable is an open TODO (see TODO).

### Deployment

For a fleet you supervise each `replio serve` process with Docker Compose, scaling one service per agent from the repo's `docker-compose.yml.example`. Each service mounts the agent folder, publishes a host-local port, and carries `restart: unless-stopped`, so Compose restarts the agent on failure and every agent exposes `GET /health` for monitoring.

Full setup is in [deploy.md](deploy.md).
