# Security

Replio is local-first and deliberately small. Its security posture rests on a few properties: an explicit per-tool permission model, worktree-scoped file access, a config-driven surface, and complete session logs that double as an audit trail. This document covers the threat model and the controls in place today.

## Permission model

Every tool call is gated by `ToolPolicy` (`src/replio/tools/policy.py`) with three actions:

- **`allow`** - runs without prompting.
- **`ask`** - prompts y/N in the loop.
- **`deny`** - the tool is filtered from the provider schema and refused on direct calls.

Resolution precedence (see [tools.md](tools.md) for the full flow):

1. Name-level `tools.deny` and the `tools.allow` allowlist.
2. The category action from `tool_permission` (`read` / `list` / `edit` / `bash` / `web` / `delegate`).
3. A per-invocation resolver (`permission_fn`) that refines the action from the tool's current arguments - e.g. `delegate` resolves per persona: a configured persona uses its own `tool_permission`, a persona outside the registry is denied (see [personas.md](personas.md)).
4. Worktree escalation: `read` / `list` / `write` tools on paths outside the worktree escalate `allow` to `ask`.

The worktree is the directory holding the local `.replio/` - the launch directory, or `--path`. A `read_file` / `list_dir` / `write_file` / `glob` / `grep` on a path outside it escalates to `ask`, so an agent cannot silently reach files beyond its scope. Launching from `~` makes home the worktree, so subdirectories do not escalate. Launch inside the project or pass `--path` for project-scoped prompting.

`bash` defaults to `ask`, so every `run_command` confirms unless `tool_permission.bash = "allow"` is set explicitly. `delegate` defaults to `allow`, refined per invocation by the target persona's own permission (a persona may set `delegate: "ask"` to confirm).

## Headless agents are confined

In headless mode (`replio serve` / `replio run`), `ask`-gated tools are denied outright - the headless UI auto-answers with the configured `--yes` / `--no` policy. An agent's reachable surface is therefore exactly its `allow` tools on paths inside its worktree. This is the isolation boundary that makes one-agent-per-process fleets safe: a crash or a misbehaving agent cannot touch another agent's folder or run commands it was not given. See [fleet.md](fleet.md).

## Delegation

The `delegate` tool runs a task under a persona as an in-process sub-agent. A sub-agent shares the caller's worktree and tool policy, narrowed by the persona's `tool_permission` carve, so it can reach exactly what the caller can minus what the carve denies. Ask-gated tools are auto-denied inside a sub-agent (no interactive confirm), so its effective permissions are the categories its carve allows. The permission resolves per invocation from the target persona: a configured persona uses its own `tool_permission` (category `delegate` defaults to `allow`; set `ask` on a persona to confirm each delegation), and a persona outside the registry is denied outright. Delegation is recorded in the session `permissions` audit array like any tool call, and each sub-agent's work persists as its own `delegate_<persona>_<ts>` session log. For delegation across trust boundaries, run separate `replio serve` processes scoped to their own folders and delegate over the API instead - see [fleet.md](fleet.md).

## Modes

Modes ([config.md](config.md)) are named postures that combine an instruction block with tool-policy overrides. The built-in `plan` mode is a read-only posture: it denies the `edit` and `bash` categories, so write and exec tools are filtered from the provider schema and refused on direct calls, and its system prompt instructs the model to investigate and propose rather than modify. Custom modes can express stronger postures (e.g. deny `mcp` as well) per deployment. The active mode is recorded on each assistant message in the session log, so the posture in effect for every turn is auditable. Mode switches are recorded as `command` messages.

## Config-driven surface

The model only sees tools whose schema passes policy filtering (`tools.allow` / `tools.deny` / `tool_permission`), and plugin activation is an explicit `plugins` list. The surface area - providers, tools, plugins, permissions - is configuration, not convention. Tool status lines are ephemeral UI and are never persisted to session files; permission decisions (each `allow` / `ask` / `deny` resolution and its outcome) are recorded in the session `permissions` array as an audit trail. Gaps against a full audit trail: session files are not hash-chained or tamper-evident (append-only by convention, not by construction), tool-result content can be redacted by `noise_tools` / `session_tool_max_chars`, and tool `analysis` is off by default (`tool_analysis`).

## Audit trail

Sessions are complete, append-only logs: every message, tool call with its arguments and result, reasoning, and error is recorded with timestamps. Compaction only trims the provider context, never the log, so any action can be reconstructed later. See [session.md](session.md). For enterprise deployments this is the base for compliance and forensics, with central aggregation and tamper-evidence as additive hardening (see [use-cases/enterprise.md](use-cases/enterprise.md)).

## Data posture

- **Local-first** - config and session logs live on your disk. All provider traffic is outbound. There is no external telemetry or logging service holding enterprise data.
- **Zero dependencies** - the core is Python stdlib only, so there is no supply chain to audit and no lockfile churn. Plugins may add third-party deps, imported lazily and only when the plugin is used.
- **API keys** - stored in config (global or local `.replio/config.json`). Keep keys out of repositories.

## Plugins

Plugins are arbitrary Python code that run with your user's privileges. Install only plugins you trust. A plugin's `register_providers` hook runs at load. Its tools run on demand like any built-in tool. The manifest declares `replio_version` and `python` compatibility ranges, and incompatible plugins are skipped at load. See [plugins.md](plugins.md) for management and the security notes.

## Prompt injection

Tool results and fetched content are untrusted input returned to the model. Defense in depth today: tools are whitelisted by policy, `ToolRegistry.execute()` drops undeclared and `null` arguments (so a hallucinated parameter cannot reach a handler), results are bounded (`session_tool_max_chars`, `noise_tools`), and `run_command` requires confirmation by default. Worktree escalation keeps file access scoped.

## Threat model at a glance

| Asset | Control |
|-------|---------|
| Filesystem | Worktree-scoped `allow`/`ask`/`deny`, escalation outside the worktree |
| Shell | `run_command` gated by `bash: ask` by default, headless auto-deny |
| Delegation | Per-persona per-invocation resolution (`delegate: allow` default, set `ask` per persona; non-registry personas denied), sub-agents auto-deny `ask` and share only the caller's carve, own `delegate_*` session logs |
| Network | Explicit tools (`web_search`, `fetch_page`), `web` permission |
| Provider context | Policy-filtered tool schema, argument cleaning, bounded tool results |
| Session data | Append-only local logs, local file ownership |
| Model | Config-driven provider/model selection, no autonomous self-modification |

## Planned hardening

Sandboxed exec (namespace/container isolation for `run_command`) and per-plugin virtualenv isolation are planned future work (see [TODO.md](../TODO.md) and [plugins.md](plugins.md)).