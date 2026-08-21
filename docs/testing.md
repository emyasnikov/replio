# Testing

Tests live in `tests/` and use the stdlib `unittest` framework - no external test runner, no network, no API key required. **Mock tests** patch provider responses so the agent loop, engine, CLI, and server are exercised without hitting a real model.

## Running tests

Run all tests:

```bash
python -m unittest discover tests
```

Run a single file:

```bash
python -m unittest tests.test_tool_calling
```

Run tests before committing changes to verify core logic isn't broken.

## Test coverage

| File | Covers |
|------|--------|
| `test_agent_loop.py` | Agent-loop behavior: single round trip, thinking persistence, graceful error bail, empty/truncated-stream multi-attempt retry, recovery hint after failed tool-call rounds, truncation error messages (configured cap vs provider default) |
| `test_bundled_plugins.py` | Bundled plugin discovery, tool registration, search service, bundled update/uninstall blocking |
| `test_cli.py` | `replio run`: JSON/text output, session-id persistence, exit codes |
| `test_commands.py` | Slash-command registration and `/help` output (aliases, subcommands, tools listed under `/tool`, mode-filtered listings) |
| `test_completion.py` | Readline tab completion: commands, session names, plugin names, tool names |
| `test_engine.py` | `Engine.chat` turn result, thinking/content separation, load-or-create sessions, ASCII auto session naming, plan-mode schema filtering, instruction injection, per-message `mode`, glyph param suffix gating, `!` error-line rendering and `show_errors` gating |
| `test_http.py` | SSE streaming: data parsing, `done` marker, multi-byte split across chunks, HTTP errors, POST-preserving redirects (loopback server) |
| `test_machine_tools.py` | `read_file` / `list_dir` behavior: numbering, offsets, headers, size probe (`limit=0`), `tool_max_result_chars` cap, error paths, `run_command` cwd validation and timeout clamp |
| `test_mcp.py` | MCP plugin: JSON-RPC framing, stdio/HTTP transports, modern/legacy negotiation, tool import + prefixing, server dispatch (`initialize`/`discover`/`tools/*`/`resources/*`), `_meta` validation, policy integration |
| `test_modes.py` | Mode resolution and policy merging: built-ins (`build`/`plan`), custom modes, unknown fallback, instruction composition |
| `test_ollama_provider.py` | Streaming provider: fragmented tool-call reassembly, thinking events, payload construction |
| `test_plugins.py` | Plugin manager: manifest compat ranges, discovery precedence, registration hooks, install/update/uninstall |
| `test_providers.py` | Provider defaults, override behavior, `detect_provider`, endpoint normalization, POST-preserving redirects |
| `test_server.py` | `replio serve` HTTP API: `/chat`, `/sessions`, `/health`, `/version` |
| `test_session_log.py` | Session model: append-only serialization, `tool_max_chars` truncation, metadata |
| `test_tool_calling.py` | Tool-calling flow: single and multiple calls, unknown tools, query refinement |
| `test_tool_policy.py` | `ToolPolicy`: allow/ask/deny, worktree escalation, deny/allowlist precedence |
| `test_tool_registry.py` | Tool registration metadata, schema, refine flags, `_config` pass-through, activity params strings, fs tool glyphs (`* List` / `* Grep`) |
| `test_ui.py` | UI sinks: glyph activity lines, status oneliner fallback, headless verbose rendering, `!` tool-error lines |

`tests/helpers.py` provides `make_chat(config_data)` - a `ChatLoop` with a mocked provider - used by most tests to drive the engine without a model.

## Live testing

Manual live tests against a real provider API are done ad-hoc, not automated. Use a local model (Ollama) or a disposable API key, and verify a turn end-to-end: streaming output, a tool call round trip, and session persistence.