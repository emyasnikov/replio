# Testing

Tests live in `tests/` and use the stdlib `unittest` framework - no external test runner, no network, no API key required. **Mock tests** patch provider responses so the agent loop, engine, CLI, and server are exercised without hitting a real model.

## Running tests

Run all tests:

```bash
python -m unittest discover tests
```

The canonical setup installs the package (`pip install -e .`), which is also what CI does. On a source checkout without installing, use `PYTHONPATH=$PWD/src` (absolute - the detached-fleet daemon changes directory, so a relative `src` would not resolve): `PluginManager` then falls back to the repo-root `plugins/` directory for the bundled plugins.

Run a single file:

```bash
python -m unittest tests.test_tool_calling
```

Run tests before committing changes to verify core logic isn't broken.

## Test coverage

| File | Covers |
|------|--------|
| `test_agent_loop.py` | Agent-loop behavior: single round trip, thinking persistence, graceful error bail, empty/truncated-stream multi-attempt retry, recovery hint after failed tool-call rounds, truncation error messages (configured cap vs provider default), auto-continue on truncation (stitch + cap + continue instruction), reasoning-only turn not flagged empty, empty-done retried, KeyboardInterrupt cancels the turn (mid-stream and after a tool call) with partial output persisted, unknown-tool results list available tools |
| `test_bundled_plugins.py` | Bundled plugin discovery, tool registration, search service, bundled update/uninstall blocking |
| `test_cli.py` | `replio run`: JSON/text output, session-id persistence, exit codes, one-shot overrides applied but never persisted, `_engine_from_args` approval wiring (explicit `--model` auto-approves, `--approve-model` grants, default does not). `replio export`: default/custom/stdout targets, unknown session. `replio models`: listing, error/empty, `main` dispatch |
| `test_config.py` | Config scopes: local-only saves, `--global` writes, `apply()` in-memory overrides (never written), unset fallback/origin, global>local merge, empty-local-does-not-shadow-global, `replio config` CLI (get/set/unset, JSON values, show-origin). `api_key` is an ordinary key - no global forcing, `0600`, or migration |
| `test_commands.py` | Slash-command registration and `/help` output (aliases, subcommands, tools listed under `/tool`, mode-filtered listings), `/connect` probe-before-commit (decline/reject, model-mismatch show offer, provider + model registry append, picker reuse, picker hidden when configured), `/model` list/`--online`/switch-touch (key marker sourced from providers.json, provider/model ref unfold + approval prompt), `/config` scope flags (`--global`/`--local`, `api_key` as a normal key incl. global writes, `-a`/`-r` scope), `/models` listing/error/empty, `/provider` warn |
| `test_completion.py` | Readline tab completion: commands, session names, plugin names, tool names |
| `test_engine.py` | `Engine.chat` turn result, thinking/content separation, load-or-create sessions, ASCII auto session naming, plan-mode schema filtering, instruction injection, per-message `mode`, glyph param suffix gating, `!` error-line rendering and `show_errors` gating, soft-result note-line rendering and `show_notes` gating, `check_connection`/`list_models` probe resolution and overrides without state mutation, `_reinit_provider` provider-registry API key resolution (no config fallback, registry custom base_url fallback when config empty), model-ref unfold + approval gate (unfolded provider/base_url/model, headless deny, `approve_models` grant, chat short-circuit, subagent type-model unfold + gate, team-run pre-check deny) |
| `test_eval.py` | Eval harness: fixture model + loading, declarative verifier (exact/must_include/avoid/max_calls/min_calls/args), metric computation (accuracy, redundant, errors, tokens), fixture discovery + precedence (plugin/global/local), cwd isolation and restore, suite aggregation |
| `test_fleet.py` | Fleet supervisor: port allocation (preferred/bind-probe fallback/in-use skip/exhaustion), `/health` probe ok + failure, manifest/state round-trip + corrupt tolerance, spawn > health > crash > restart > down via `sys.executable -c` mock servers, `max_restarts` give-up, unhealthy-threshold restart, disabled gate, log files, env seams (`REPLIO_FLEET_PORT`), `replio fleet` CLI (init/add/remove/status/restart/config incl. type inline + unknown-type error), detached-daemon end-to-end (up --detach, status, down) |
| `test_http.py` | SSE streaming: data parsing, `done` marker, multi-byte split across chunks, HTTP errors, POST-preserving redirects (loopback server) |
| `test_jobs.py` | Job model + registry (round-trip incl. `require_approval`/`task_file`/`approve_model`/`created_at`, runnable + ready-to-run gates, corrupt file tolerance), cron parser (steps/ranges/lists/dom/dow/the restrictive day rule, leap day), `next_run`/`compute_next_run`/`parse_dt`, scheduler run/tick under a mocked engine (verified/failed, retries with backoff, per-attempt history, unknown type, one-shot `at`, approval gates, per-run `require_approval` park/re-arm, run memory write + injection, per-run session naming + collision dedupe + `--session` stability, run content capture), `_build_engine` type-skill injection (present/missing), task file template/linkage/missing-file failure, status/list/show rendering, `replio jobs` CLI (add/approve/list, `--file`, edit, status output, stop, auto-approval, bad cron, duplicates, run exit codes + content printing) |
| `test_models.py` | `ModelRegistry` (approved-model history in global `models.json`): path under `GLOBAL_DIR`, put/find by (provider, model), dedupe + last_used, distinct models keep separate entries, touch, remove, grouped, reload, corrupt-file tolerance, old per-model-key shape dropped without migration, `GLOBAL_DIR` default |
| `test_providers_registry.py` | `ProviderRegistry` (global `providers.json`): path under `GLOBAL_DIR`, put/find/dedupe per provider, empty key keeps existing, base_url stored only when given, key/base_url lookup, touch, `0600` when keyed, reload, corrupt-file tolerance, remove, `GLOBAL_DIR` default. `resolve_model_ref`: known/unknown provider, bare model, no-default provider, empty parts, plugin providers |
| `test_modes.py` | Mode resolution and policy merging: built-ins (`build`/`plan`), custom modes, unknown fallback, instruction composition |
| `test_ollama_provider.py` | Streaming provider: fragmented tool-call reassembly, thinking events (`reasoning_content` and `reasoning` keys), payload construction |
| `test_plugins.py` | Plugin manager: manifest compat ranges, discovery precedence, registration hooks (tools/providers/commands/services/types/teams/skills + hook-failure status), `_bundled_dir` fallback (source layout + forced import failure), install/update/uninstall, `replio plugins test` (+ `load_plugin_test_suite`) |
| `test_skills.py` | `SkillRegistry`: local/global dir scans, plugin/global/local merge and precedence, origins, put/remove round-trip, reload (disk re-read + plugin-manager re-apply), `skills_section`, `/skill` command (list/show/new override/remove, plugin remove rejected) |
| `test_team_run.py` | `Engine.run_team`: brief builder (task + prior results + handoff + memory + task hint, prior-result truncation), sequential stage execution with per-stage `sub_*` sessions + parent linkage + exact brief persistence, stage mode override + caller-mode inheritance, stop-on-failure, unknown-stage-type stop, zero stages, rolling team-memory write (summarized + prior-seeded + fallback), `/team run` command output (stages + final result, unknown team, usage) |
| `test_teams.py` | `TeamRegistry`: bundled/plugin/global/local merge and precedence, origins, stage round-trip (dict + short-string forms), put/remove, reload (disk re-read + plugin-manager re-apply), `/team` command (list/show/new override/remove, `list <tag>` filter, bundled remove rejected) |
| `test_subagent.py` | In-process sub-engine: provider/plugin/worktree inheritance, type prompt/mode/tool_permission application, type-skill system-prompt injection (present/missing/empty/no-skills), model override, `NullUI`, unknown type, full `run_subagent` flow + persisted `sub_*` session with `parent_id`, ask-gated tool cancellation, parent `sub_sessions` linkage |
| `test_delegate.py` | `delegate` tool: type allow default (no prompt) / `ask` confirm grant-decline / unknown-type deny, `delegate_echo` on/off display + sub footer, `/tool delegate` single print, empty-content log-summary fallback, sub-agent session persistence + resolver actions |
| `test_types.py` | `TypeRegistry`: bundled/plugin/global/local merge and precedence, origins (bundled/plugin/local/global origin), tags roundtrip + merge, put/remove/reload (disk re-read + plugin-manager re-apply), `/type` command (list/show/new override/remove, `list <tag>` filter, bundled remove rejected) |
| `test_providers.py` | Provider defaults, override behavior, `detect_provider`, endpoint normalization, POST-preserving redirects, `check_connection` probe (success/empty/model note/HTTP/network), `list_models` silent-on-error |
| `test_repl_input.py` | REPL input: multi-line `"""`/`'''` block detection, framing strip (pure, lead-in, indentation preserved), EOF exit during an open block, slash commands single-line |
| `test_server.py` | `replio serve` HTTP API: `/chat`, `/sessions`, `/health`, `/version` |
| `test_session_log.py` | Session model: append-only serialization, `tool_max_chars` truncation, metadata |
| `test_session_render.py` | Session Markdown export: renderer output per role, error section, `/session export` dispatch and file/stdout targets |
| `test_subagent.py` | In-process sub-engine: provider/plugin/worktree inheritance, type prompt/mode/tool_permission application, model override, `NullUI`, unknown type, full `run_subagent` flow + persisted `sub_*` session with `parent_id`, ask-gated tool cancellation, parent `sub_sessions` linkage |
| `test_tool_calling.py` | Tool-calling flow: single and multiple calls, unknown tools, query refinement |
| `test_tool_policy.py` | `ToolPolicy`: allow/ask/deny, worktree escalation, deny/allowlist precedence, per-invocation resolver (refines non-deny base, skipped without args, cannot override deny list) |
| `test_tool_registry.py` | Tool registration metadata, schema, refine flags, note-result predicates, `_config` pass-through, activity params strings, fs tool glyphs (`* List` / `* Grep`), `permission_fn` storage + `resolver_for` |
| `test_ui.py` | UI sinks: glyph activity lines, status oneliner fallback, headless verbose rendering, `!` tool-error lines, word-streaming buffering (boundary flush, tail flush, off-mode immediate writes, markdown across boundaries, flush before status/confirm), confirm `?` glyph at line start, confirm re-raises KeyboardInterrupt / returns False on EOF |

`tests/helpers.py` provides `make_chat(config_data)` - a `ChatLoop` with a mocked provider - used by most tests to drive the engine without a model.

## Plugin test suites

Each bundled plugin ships its unit tests in its own directory (`plugins/<name>/tests/`), covering the plugin's tools and helpers without touching the core. They are discovered by the core suite through `tests/test_plugin_suites.py` (registered via `load_tests`), so `python -m unittest discover tests` runs everything. A single plugin's suite runs standalone with `python plugins/<name>/tests/<file>.py`, and headless via `replio plugins test <name>` (or `replio plugins test` for every plugin with a suite).

## Live testing

Manual live tests against a real provider API are done ad-hoc, not automated. Use a local model (Ollama) or a disposable API key, and verify a turn end-to-end: streaming output, a tool call round trip, and session persistence.