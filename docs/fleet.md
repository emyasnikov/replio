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

- **Worktree scoping**: the tool policy treats the launch directory (`--path`, or the current directory) as the worktree. `read_file` / `list_dir` / `write_file` / `glob` / `grep` on a path outside it escalate from `allow` to `ask` (tools/policy.py:35). A doc agent cannot touch files in another agent's folder unless its config says so.
- **Headless auto-deny**: in `serve`/`run` mode, `ask`-gated tools are denied outright (ui.py `HeadlessUI.confirm` answers `auto == 'allow'`). An agent's reachable surface is therefore exactly `allow` tools on paths inside its worktree, plus `--yes` explicit approvals.
- **Tool allow/deny**: `tools.allow` (whitelist mode) and `tools.deny` narrow the registered schema the model sees. A web agent sets `tools.deny: [run_command, write_file]`. A code agent denies `web_search, fetch_page`.
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
  "tools.allow": ["glob", "read_file", "write_file", "run_command", "pdf2text", "watch_folder", "search_index"],
  "tool_permission": { "read": "allow", "list": "allow", "edit": "allow", "bash": "allow", "web": "allow" },
  "plugins": ["replio-core-fs", "replio-core-exec", "replio-core-doc-agent"]
}
```

Launch it, and peers talk to it over the same `POST /chat` API used everywhere:

```bash
replio serve --path agents/docs --port 8781 &
curl localhost:8781/chat -X POST -d '{"prompt": "What does spec-42.pdf say?", "session_id": "docs-pool"}'
```

## Deployment

For a fleet you supervise each `replio serve` process with Docker Compose, scaling one service per agent from the repo's `docker-compose.yml.example`. Each service mounts the agent folder, publishes a host-local port, and carries `restart: unless-stopped`, so Compose restarts the agent on failure and every agent exposes `GET /health` for monitoring.

Full setup is in [deploy.md](deploy.md).
