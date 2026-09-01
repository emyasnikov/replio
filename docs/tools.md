# Tools

Tools are how the model acts. The `ToolRegistry` (`src/replio/tools/registry.py`) is the single dispatch point: the model invokes tools via OpenAI-compatible function calling, slash commands are thin wrappers that call the same `execute()`, and the loop never special-cases tool names - per-tool behavior comes from registration metadata.

This page is the reference: what the registry supports, the bundled tools, and the policy that gates them. For how to design, name, and describe a new tool so agents use it well, see [writing-tools.md](writing-tools.md).

Tool definitions follow the OpenAI function calling JSON schema format. The model sees the schema (filtered by policy), requests a tool call, and the loop executes it and feeds the result back into the conversation.

## Bundled tools

The built-in web and machine tools ship as bundled plugins, loaded out of the box:

| Tool | Plugin | Category | Permission | Purpose |
|------|--------|----------|------------|---------|
| `web_search` | replio-core-websearch | `search` | `web` | Web search (alias `search`) |
| `fetch_page` | replio-core-websearch | `read` | `read` | Fetch and extract page text |
| `open` | replio-core-websearch | `read` | `read` | Open a `web_search` result by `id` or a URL directly |
| `read_file` | replio-core-fs | `read` | `read` | Read a file with numbered lines |
| `list_dir` | replio-core-fs | `read` | `list` | List a directory (`depth` for trees) |
| `write_file` | replio-core-fs | `write` | `edit` | Create/overwrite/append a file |
| `glob` | replio-core-fs | `search` | `read` | Recursive pattern lookup |
| `grep` | replio-core-fs | `search` | `read` | Regex content search (`file:line:` results, alias `find`) |
| `run_command` | replio-core-exec | `exec` | `bash` | Run a shell command with timeout |
| `delegate` | core | `delegate` | `delegate` | Run a task under a persona as a sub-agent |

Plugins register additional tools the same way. They automatically inherit tool policy, `/tool`, `/help`, query refinement, `noise_tools`, and session logging. See [plugins.md](plugins.md).

## The tool loop

1. The provider's `chat()` stream yields a `tool_calls` event with the requested function calls.
2. The loop appends an `assistant` message with the `tool_calls` and `thinking`.
3. Each call is checked against the tool policy, then executed through `ToolRegistry.execute()`.
4. Each result is appended as a `tool` message (with `tool_call_id` and the tool name), optionally with a one-line `analysis` when `tool_analysis` is enabled.
5. The loop continues with the enriched context until the model answers.

Ctrl-C in the REPL cancels the running turn - streaming and any in-flight tool execution are aborted, partial output is persisted, a `(cancelled)` note prints, and the prompt returns. At a y/N confirm prompt it cancels the whole turn too (typing `n` still declines just that tool). This mirrors the headless behavior, where `replio run` exits non-zero on a cancelled turn.

## Running a tool directly

`/tool <name> {"key": "value"}` runs any registered tool from the REPL, routed through the same policy. `/help <tool>` shows a tool's description, parameters, category, and permission.

## Registration metadata

Tools are registered with `@registry.register(name, description, parameters)` plus optional metadata that shapes loop behavior:

| Key | Description |
|-----|-------------|
| `refine` | Auto-refine short `query` args via a lightweight model call, gated by the `query_refine` config |
| `category` | `search` / `read` / `write` / `exec` / `ask` / `todo` / `delegate` / `mcp` - drives the default activity glyph and verb |
| `permission` | The `tool_permission` key that gates the tool: `read` / `list` / `edit` / `bash` / `web` / `mcp` |
| `permission_fn` | Optional `Callable[[dict], str]` resolving the action (`allow`/`ask`/`deny`) from the current arguments - refines a non-`deny` base action at call time (see `delegate`) |
| `path_arg` | Which parameter is a filesystem path, for worktree scope checks |
| `key_arg` | Which argument appears in status/confirm labels and glyph activity lines |
| `glyph` / `verb` | Per-tool activity-line overrides (e.g. `glob` uses `* Glob`, `fetch_page` uses `↓ Fetch`) |
| `status` | A `Callable[[dict], str]` receiving the cleaned args and returning a block whose first line becomes the `[tool: <value>]` oneliner and the rest render as dimmed detail lines (used by `write_file` to preview/diff the written text) |
| `echo` | When true, the tool result is printed dimmed below the status oneliner (used by `run_command`) |
| `short` | Short label for `/help` listing (defaults to the description truncated) |
| `aliases` | Extra tool names resolving to this tool (e.g. `read`/`view` for `read_file`, `search` for `web_search`) - absorbed at call time, never advertised to the provider |
| `param_aliases` | Caller-side parameter synonyms mapped onto declared parameters (e.g. `cursor` -> `offset`, `query` -> `pattern`) |

`ToolRegistry.execute()` passes only arguments declared in the tool's schema - undeclared and `null`-valued arguments (e.g. a hallucinated `recursive`, or `depth: null`) are dropped, not forwarded to the handler. It also passes the engine `Config` to handlers that declare a `_config` keyword argument (e.g. `def read_file(path, offset=1, limit=500, _config=None)`), so a tool can read config keys like `tool_max_result_chars` without exposing them to the model.

Models often guess tool and argument names rather than reading the schema (`search` for `web_search`, `find` for `grep`, `cursor` for `offset`). `aliases` (extra tool names resolving to a tool, e.g. `search`/`find`) and `param_aliases` (caller-side parameter synonyms, e.g. `cursor -> offset`, `query -> pattern`) let the registry absorb that dialect without advertising it in the schema. A tool the model calls that is not registered at all returns `Error: unknown tool "<name>. Available tools: <...>"` - the loop lists the registered tools so the model can pick a real one instead of retrying the same bogus name. `open` also tolerates a URL string passed in its `id` argument by treating it as the URL.

## Adding a tool

1. Open the plugin or module where the tool belongs.
2. Use the `@registry.register(name, description, parameters)` decorator.
3. `parameters` follow the OpenAI function calling JSON schema format.
4. The handler receives keyword arguments matching the schema.
5. Return a string - the tool result injected into the conversation.
6. Add the optional metadata above for loop behavior, permissions, and display.

Example:

```python
@registry.register(
    name='pdf2text',
    description='Extract text from a PDF',
    parameters={'type': 'object',
                'properties': {'path': {'type': 'string'}},
                'required': ['path']},
    permission='read',
    path_arg='path',
    key_arg='path',
)
def pdf2text(path):
    return extract(path)
```

## Result size and large files

Tool results are sent to the model verbatim. Nothing is truncated unless `tool_max_result_chars` is set (default `0` = unlimited). Setting it caps every tool result at N characters with a trailing `... (truncated)` marker.

`read_file` helps the model page through large files without hitting a cap:

- Every result header reports the total size: `# <path> - <N> lines, <M> chars` (plus `(showing a-b)` for partial windows), so the model learns a file's size from the first read.
- `limit=0` returns just the header as a size probe - the model can check a file's size before committing to a read.
- A large file is then read in windows via `offset` / `limit` arguments (`read_file(path, offset=1, limit=200)`, then `offset=201`, ...).

## Tool policy

Every tool call is gated by `ToolPolicy` (`src/replio/tools/policy.py`), the single permission resolution point. The loop and `/tool` both route through it - never special-case tool names for permission logic.

Actions are `allow` (no prompt), `ask` (y/N confirm in the loop), or `deny` (tool filtered from the provider schema and refused on direct calls).

Every permission resolution and its outcome (granted / declined / denied) is recorded to the session `permissions` array as an append-only audit trail - see [session.md](session.md).

Resolution precedence:

1. **Name-level** - `tools.deny` (always denied) and `tools.allow` (when non-empty, an allowlist - everything else is denied).
2. **Category action** - the `tool_permission.<key>` action for the tool's `permission` key. `deny` here filters the tool from the provider schema and from tool listings, not just direct calls.
3. **Per-invocation resolver** - a tool may declare a `permission_fn` that refines the action from its current arguments (e.g. `delegate` resolves per persona: a configured persona uses its own `tool_permission` with `delegate` defaulting to `ask`, a persona outside the registry is `deny`). The resolver only refines a non-`deny` base action and is skipped when no arguments are available, so schema filtering (`allowed()`) keeps the tool visible for `ask`/`allow` categories.
4. **Worktree escalation** - `read` / `list` / `write` tools pointing outside the project worktree escalate from `allow` to `ask`.

Modes ([config.md](config.md)) layer over the base policy: a mode's `tool_permission` merges over the base (mode wins per key), its `tools.deny` appends, and its `tools.allow` replaces when non-empty. The built-in `plan` mode denies the `edit` and `bash` categories, so write and exec tools are filtered from the schema and refused on direct calls. Switch with `/mode <name>` in the REPL or `--mode <name>` on `replio run` / `replio serve`.

### Worktree

The worktree is the directory holding the local `.replio/` - the launch directory, or `--path`. Launching from `~` makes the whole home directory the worktree, so subdirectories (including other projects) do not escalate. Launch inside the project or pass `--path` for project-scoped prompting. `bash` defaults to `ask`, so every `run_command` confirms unless `tool_permission.bash = "allow"`.

In headless mode (`run` / `serve`), `ask`-gated tools are denied outright (`--yes` / `--no` override), so an agent's reachable surface is exactly its `allow` tools on paths inside its worktree.

## Configuration

Tool behavior is controlled by config keys (see [config.md](config.md) for the full schema and defaults):

| Key | Default | Controls |
|-----|---------|----------|
| `tool_calling` | `true` | Enable OpenAI-compatible function calling |
| `tools.allow` | `[]` | Name-level allowlist. When non-empty, only these tools are callable |
| `tools.deny` | `[]` | Name-level deny list (takes precedence over allow) |
| `tool_permission` | *(see config.md)* | Category actions - `read`/`list`/`edit`/`bash`/`web`/`mcp` -> `allow`/`ask`/`deny` |
| `tool_status_visible` | `true` | Show dimmed tool status in the REPL |
| `glyph_lines` | `true` | Typed activity lines for mapped categories, else the `[tool: arg]` oneliner |
| `tool_analysis` | `false` | Model-generated one-line analysis of each tool result (log-only) |
| `tool_max_result_chars` | `0` | Cap every tool result at N chars (`0` = unlimited) |
| `session_tool_max_chars` | `0` | Cap persisted tool-result content in session files (`0` = unlimited) |
| `noise_tools` | `["fetch_page"]` | Tool results replaced by a marker in persisted sessions |
| `query_refine` | `false` | Auto-refine short `query` args via a lightweight model call |
| `query_refine_min_words` | `3` | Minimum query length before refinement applies |
| `query_refine_context` | `4` | Recent-message context injected into refinement |
| `search_results` | `5` | Number of results `web_search` returns |

Handlers can read config at runtime via the `_config` keyword argument the registry passes only when declared.

See [config.md](config.md) for the `tools.allow`, `tools.deny`, and `tool_permission` keys, and [security.md](security.md) for the threat model.

## Status and activity lines

Tool status is ephemeral REPL/CLI UI - it is never persisted to session files (tool calls and results are already recorded there). Registered tools render a typed activity line - `<glyph> <verb> <key_arg>` (e.g. `← Read README.md`, `→ Write test.md`, `$ Run pytest`) - gated by the `glyph_lines` config (default `true`). Category defaults map to glyphs: read `←` Read, write `→` Write, search `%` Search, exec `$` Run, ask `~` Ask, todo `-` Todo, delegate `↳` Call. Tools without a mapped category fall back to the `[tool: key_arg]` oneliner plus any `status` detail lines. Filesystem tools use the `*` glyph with distinct verbs: `* Glob`, `* List`, `* Grep`.

When `glyph_params` is on (default `true`), the parameters the model passed - excluding the one already shown in the label - are appended: `← Read engine.py [offset=299, limit=85]`, `$ Run pytest [cwd=/workspace, timeout=600]`. Confirm prompts show the same suffix so the cwd, timeout, and other arguments are visible before approving.

When a tool call fails, the first line of its `Error:` result is echoed as a dimmed `! Error: ...` line under the activity line (gated by the `show_errors` config, default `true`). This applies to every tool through the shared dispatch point - the agent loop, `/tool`, and policy-denied calls alike.

Soft tool results - short one-line informational notes a tool returns instead of content, like `(empty file)`, `(empty directory)`, `(no matches for "x")`, `(end of content)`, or `No search results found.` - are surfaced as a dimmed info line under the activity line (gated by the `show_notes` config, default `true`). A tool opts into this by declaring a `note` predicate (a callable taking the raw result and returning whether it is a note) in its registration metadata. The result itself is unchanged and still fed to the model.