# Writing tools for agents

Tools are how a Replio agent acts. The model plans, the `ToolRegistry` dispatches, and the agent loop feeds every tool result back into the conversation until the model answers. A tool is a contract between a deterministic system (your tool implementation) and a non-deterministic agent (the model). The model may call the right tool with the wrong parameters, call the wrong tool, call too few tools, or misread a result. This guide is about writing tools that hold up under that uncertainty, across any OpenAI-compatible provider, weak backends included.

The registry mechanics (registration metadata, policy, aliases, `clean_args`) are the reference in [tools.md](tools.md). This page is the craft: which tools to build, how to name them, what to return, and how to describe them. The principles are adapted from Anthropic's "Writing effective tools for agents" and shaped to Replio's single-loop, zero-dependency design.

## Choosing the right tools

More tools does not mean a better agent. Every tool definition is loaded into the model's context on every turn, and overlapping tools actively mislead selection. Build a few thoughtful tools that target high-impact workflows, and scale up only when a real gap shows up.

- Prefer search and point tools over dump-everything tools. An agent wastes its limited context reading irrelevant results. `grep` returns only matching `file:line: text` lines. `glob` locates a path before it is read. `file_read` reports `N lines, M chars` in its header so the agent can probe a file's size with `limit=0` before committing to a read.
- Consolidate operations that are usually chained. `file_write` folds create, overwrite, and append into one call behind a `mode` enum. `delegate` runs a whole task under a persona as a single call. A consolidated tool offloads multi-step reasoning from the model's context into the tool itself.
- Do not wrap a function or API endpoint just because you can. A tool needs a clear agent affordance: the model must be able to decide from its description alone when to call it and what to do with the result.
- Avoid near-duplicate tools. Two tools that fetched a web page (`open` and `fetch_page`) confused agents until they were merged into one `web_fetch` that takes `url` or a search-result `id`. If two tools overlap, merge them or delete one.

## Naming and namespacing

Tool names are how the model selects behavior, so they should be distinct, purposeful, and grouped by domain.

- Give every tool a clear, distinct purpose and a name that states it. `web_search`, `web_fetch`, `file_read`, `list_dir`, `file_write`, `glob`, `grep`, `run_command` all read as one distinct action each.
- Namespace by domain when a surface grows. The bundled plugins already do this by module (`replio-core-websearch` exposes `web_search`, `web_fetch`), and MCP tools use the `mcp_` prefix. Prefixing (`web_`, `file_`, `mcp_`) helps the model pick the right tool when many are loaded.
- Advertise canonical names only, and absorb model dialect with `aliases`. The provider schema shows `run_command`, not `bash` or `exec`, and `web_fetch`, not `open` or `fetch_page`. Aliases resolve at call time, so a model that still says `open`, `search`, or `find` gets the real tool anyway. Advertising both spellings doubles the tool list in every request for no benefit.
- Name parameters unambiguously. Prefer `include` over `glob`, `pattern` over `query` inside `grep`, and concrete nouns over pronouns. A parameter named `path` with a description is clearer than a bare `file`.

## Returning meaningful context

Tool results are fed back verbatim into the model's context. Return high-signal information that directly informs the next step, and prefer interpretable language over technical identifiers.

- Resolve and report natural identifiers. `file_read` and `file_write` resolve absolute paths. `grep` returns `file:line: text` so the model can act on the location. No raw UUIDs or opaque handles appear in Replio's tools.
- Report sizes and boundaries so the agent can decide. `file_read` puts the total line and char count in its header and marks partial windows with `(showing a-b)`. `web_fetch` reports `[offset N of M chars]` when content continues.
- Keep results deterministic and complete for the task. The same input should produce the same output, and a result should not depend on unrelated state.

## Optimizing tool responses for token efficiency

Context is the model's scarcest resource. Give every potentially large response pagination, filtering, or a sensible cap, and make the truncation itself steer the agent.

- Page large reads. `file_read(path, offset=1, limit=200)` then `offset=201` walks a file window by window. `web_fetch` accepts the `offset` its marker reports. Both let the agent pull only what it needs.
- Cap with sensible defaults. `glob` stops at 200 matches and `grep` at 100, each with a `... (showing first N matches)` marker. `list_dir` caps entries via `list_dir_max_entries` (default 200) with a `... (showing first N of M entries)` marker. The `tool_max_result_chars` config key is the hard cap for every tool result (default 100000, `0` = unlimited), so tools should still self-cap below it.
- Offer narrowing parameters. `grep`'s `glob` filter limits which files are searched. `list_dir`'s `depth` bounds a tree. Filters and ranges let the agent ask for less.
- Make markers actionable. A marker that says how to continue (`send "continue"`, `use cursor=N`, `showing 5-7`) converts a truncated response into the next tool call instead of a dead end.
- Steer toward small targeted calls. A description that says "use many small searches" or "use offset to page" changes behavior more reliably than a bigger cap.

## Prompt-engineering descriptions and schemas

Descriptions are loaded into the model's context on every turn. Write each one the way you would describe the tool to a new hire, and make the schema the single source of truth.

- State the purpose, the output format, and the alternatives in the description. `file_read` explains the header, the `limit=0` size probe, and paging. `glob` shows example patterns (`"**/*.py"`, `"src/**/chat.py"`). `grep` states its `file:line:` result format. `run_command` documents stdout, stderr, and exit code.
- Say when NOT to use a tool, and point at the right one. Error text already does this at runtime (see below). A description that preempts the confusion ("use list_dir for directories") saves calls.
- Enforce the contract with types, enums, and `required`. The registry passes only declared, non-null arguments to the handler, so a strict schema is the model's only input surface. Use an enum for closed sets (file_write's `mode`), and always describe each parameter.
- Keep descriptions and implementations self-consistent. When a tool's behavior changes, update its description in the same change.

## Registration metadata that shapes behavior

Registration metadata drives more than the schema. It shapes confirmation, display, refinement, and permissions without special-casing tool names in the loop.

| Metadata | What it does for the agent |
|----------|----------------------------|
| `refine` | A short `query` is rewritten by a lightweight model call before `web_search` runs, so vague queries still work |
| `permission` / `permission_fn` | Gates the call with `allow` (no prompt), `ask` (y/N confirm), or `deny`. `permission_fn` resolves per invocation from the arguments (see `delegate`) |
| `path_arg` | Marks the filesystem path parameter so worktree escalation applies |
| `key_arg` | The argument shown in confirm prompts and activity lines, so the human sees what will happen |
| `aliases` / `param_aliases` | Absorb model-dialect tool and argument names at call time without advertising them |
| `note` | A predicate marking soft one-line results (`(no matches)`, `(empty file)`) so they render as a dimmed note, not an error |
| `status` / `echo` / `glyph` / `verb` | Ephemeral REPL activity lines (`* Grep`, `↓ Fetch`) and result previews that never reach the session log |

Full reference in [tools.md](tools.md). The policy and worktree rules that gate `permission` are in [tools.md](tools.md) and [security.md](security.md).

## Errors and soft results

Error responses are guidance, not telemetry. When a call fails, tell the model what it can do instead.

- Start with `Error:` and a one-line actionable message. Replio's filesystem tools set the pattern: `Error: X is a directory (use list_dir instead)`, `Error: X is not a directory (use file_read instead)`, `Error: file not found: X`. Each suggests the correct tool.
- Do not return tracebacks or opaque codes. The first line of an `Error:` result is echoed dimmed in the REPL, so the model and the human see the same guidance.
- Use a `note` predicate for informational one-liners that are not failures. `(no matches for "x")`, `(empty file)`, `(end of content)`, and `No search results found.` are normal outcomes, and a dimmed note beats a red error line.

## Evaluating your tools

Measure how well a model uses a tool before you trust it. Replio does not ship an agent-level tool-evaluation harness yet (planned, see TODO and PLAN), but you can evaluate today with the pieces that exist.

- Build a mock-provider loop test. The test suite runs the full agent loop against a stubbed `provider.chat` with no network and no API key. `tests/test_tool_calling.py`, `tests/test_agent_loop.py`, and the `make_chat` / `make_engine` helpers in `tests/` are the pattern. Drive the loop with a tool-call event and assert the model-visible result and the session messages.
- Exercise a tool directly with `/tool <name> {"args": ...}` from the REPL. It routes through the same policy, `clean_args`, and display as a loop call, so it is a fast sanity check for argument handling and result format.
- Read the session logs for misbehavior. A session that shows wrong-tool selection, repeated parameter errors, or the same search re-run means the description, naming, or schema is unclear. Models trained on tool-use data often reach for `open` to fetch a URL. The `open` alias absorbs that habit while the schema advertises `web_fetch`.
- Compare providers. Replio standardizes on OpenAI-compatible tool calling, but models differ sharply in how they parse schemas. Run the same task against Ollama and a hosted OpenAI-compatible endpoint and watch which tools each reaches for. Weak backends are exactly where naming, caps, and description quality pay off.

Metrics worth watching: redundant tool calls (pagination or caps too tight), invalid-parameter errors (descriptions unclear or the schema too loose), and context bloat (a tool returning more than the task needs).

## Checklist

- The tool has one distinct purpose and a name that states it.
- The description says what it does, the output format, and when not to use it, with an example.
- The schema uses explicit parameter names, types, enums, and `required`.
- The result is high-signal, deterministic, and interpretable, with no raw identifiers.
- Large results paginate or cap with an actionable marker.
- Errors start with `Error:` and suggest the correct alternative.
- Soft outcomes use a `note` predicate.
- Dialect names are `aliases`, not advertised schemas.
- The tool was exercised via `/tool` and a mock-provider loop test.