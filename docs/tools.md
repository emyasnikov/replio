# Tools

Tools are how the model acts. The `ToolRegistry` (`src/replio/tools/registry.py`) is the single dispatch point: the model invokes tools via OpenAI-compatible function calling, slash commands are thin wrappers that call the same `execute()`, and the loop never special-cases tool names - per-tool behavior comes from registration metadata.

Tool definitions follow the OpenAI function calling JSON schema format. The model sees the schema (filtered by policy), requests a tool call, and the loop executes it and feeds the result back into the conversation.

## Bundled tools

The built-in web and machine tools ship as bundled plugins, loaded out of the box:

| Tool | Plugin | Category | Permission | Purpose |
|------|--------|----------|------------|---------|
| `web_search` | replio-core-websearch | `search` | `web` | Web search |
| `fetch_page` | replio-core-websearch | `search` | `web` | Fetch and extract page text |
| `read_file` | replio-core-fs | `read` | `read` | Read a file with numbered lines |
| `list_dir` | replio-core-fs | `read` | `list` | List a directory (`depth` for trees) |
| `write_file` | replio-core-fs | `write` | `edit` | Create/overwrite/append a file |
| `glob` | replio-core-fs | `search` | `read` | Recursive pattern lookup |
| `grep` | replio-core-fs | `search` | `read` | Regex content search (`file:line:` results) |
| `run_command` | replio-core-exec | `exec` | `bash` | Run a shell command with timeout |

Plugins register additional tools the same way. They automatically inherit tool policy, `/tool`, `/help`, query refinement, `noise_tools`, and session logging. See [plugins.md](plugins.md).

## The tool loop

1. The provider's `chat()` stream yields a `tool_calls` event with the requested function calls.
2. The loop appends an `assistant` message with the `tool_calls` and `thinking`.
3. Each call is checked against the tool policy, then executed through `ToolRegistry.execute()`.
4. Each result is appended as a `tool` message (with `tool_call_id` and the tool name), optionally with a one-line `analysis` when `tool_analysis` is enabled.
5. The loop continues with the enriched context until the model answers.

## Running a tool directly

`/tool <name> {"key": "value"}` runs any registered tool from the REPL, routed through the same policy. `/help <tool>` shows a tool's description, parameters, category, and permission.

## Registration metadata

Tools are registered with `@registry.register(name, description, parameters)` plus optional metadata that shapes loop behavior:

| Key | Description |
|-----|-------------|
| `refine` | Auto-refine short `query` args via a lightweight model call, gated by the `query_refine` config |
| `category` | `search` / `read` / `write` / `exec` / `ask` / `todo` / `delegate` - drives the default activity glyph and verb |
| `permission` | The `tool_permission` key that gates the tool: `read` / `list` / `edit` / `bash` / `web` |
| `path_arg` | Which parameter is a filesystem path, for worktree scope checks |
| `key_arg` | Which argument appears in status/confirm labels and glyph activity lines |
| `glyph` / `verb` | Per-tool activity-line overrides (e.g. `glob` uses `* Glob`, `fetch_page` uses `↓ Fetch`) |
| `status` | A `Callable[[dict], str]` receiving the cleaned args and returning a block whose first line becomes the `[tool: <value>]` oneliner and the rest render as dimmed detail lines (used by `write_file` to preview/diff the written text) |
| `echo` | When true, the tool result is printed dimmed below the status oneliner (used by `run_command`) |
| `short` | Short label for `/help` listing (defaults to the description truncated) |

`ToolRegistry.execute()` passes only arguments declared in the tool's schema - undeclared and `null`-valued arguments (e.g. a hallucinated `recursive`, or `depth: null`) are dropped, not forwarded to the handler.

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

## Tool policy

Every tool call is gated by `ToolPolicy` (`src/replio/tools/policy.py`), the single permission resolution point. The loop and `/tool` both route through it - never special-case tool names for permission logic.

Actions are `allow` (no prompt), `ask` (y/N confirm in the loop), or `deny` (tool filtered from the provider schema and refused on direct calls).

Resolution precedence:

1. **Name-level** - `tools.deny` (always denied) and `tools.allow` (when non-empty, an allowlist - everything else is denied).
2. **Category action** - the `tool_permission.<key>` action for the tool's `permission` key.
3. **Worktree escalation** - `read` / `list` / `write` tools pointing outside the project worktree escalate from `allow` to `ask`.

### Worktree

The worktree is the directory holding the local `.replio/` - the launch directory, or `--path`. Launching from `~` makes the whole home directory the worktree, so subdirectories (including other projects) do not escalate. Launch inside the project or pass `--path` for project-scoped prompting. `bash` defaults to `ask`, so every `run_command` confirms unless `tool_permission.bash = "allow"`.

In headless mode (`run` / `serve`), `ask`-gated tools are denied outright (`--yes` / `--no` override), so an agent's reachable surface is exactly its `allow` tools on paths inside its worktree.

See [config.md](config.md) for the `tools.allow`, `tools.deny`, and `tool_permission` keys, and [security.md](security.md) for the threat model.

## Status and activity lines

Tool status is ephemeral REPL/CLI UI - it is never persisted to session files (tool calls and results are already recorded there). Registered tools render a typed activity line - `<glyph> <verb> <key_arg>` (e.g. `← Read README.md`, `→ Write test.md`, `$ Run pytest`) - gated by the `glyph_lines` config (default `true`). Category defaults map to glyphs: read `←` Read, write `→` Write, search `%` Search, exec `$` Run, ask `~` Ask, todo `-` Todo, delegate `↳` Call. Tools without a mapped category fall back to the `[tool: key_arg]` oneliner plus any `status` detail lines.