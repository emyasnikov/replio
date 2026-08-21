# Replio - Execution Plan

Working backlog for the next tasks, ranked by effort, urgency (hardening current functionality), and importance for the documented use cases (`docs/use-cases/`) and competitive positioning (`docs/vs/`). Source documents: `AGENTS.md`, `TODO.md`, `CHANGELOG.md`, all `docs/use-cases/*`, all `docs/vs/*`.

## Method

- Effort: relative to this codebase (S = under a day, M = 1-3 days, L = weeks).
- Urgency: how much the task hardens or de-risks existing functionality.
- Importance: coverage of documented use-case gaps and competitor features named in `docs/vs/`.

## Tier 1 - do next (small effort, hardens core, high value)

| Task | Effort | Urgency | Importance | Why |
|------|--------|---------|------------|-----|
| Session export to Markdown | S-M | Medium | High | Cross-cutting: enterprise compliance export, research citation trail, personal journal, small-biz handover; prerequisite for sharing links. |
| Config validation (test connection on change) | S | High (onboarding) | Medium | Broken provider config is top friction; `/connect` already has the plumbing. |
| Multi-line input | S | Medium (REPL) | Medium | `"""`/`'''` block detection; pure REPL hardening. |
| Word-level streaming buffering | S | Low-Med (polish) | Medium | Stops mid-word breaks; visible output quality. |

## Tier 2 - next (medium effort, high use-case + competitive value)

| Task | Effort | Why |
|------|--------|-----|
| `git` tool | M | Developer.md + claude-code/opencode parity (status/diff/commit). |
| Custom system prompts per session | S-M | Enterprise per-site instructions; groundwork for `/agent`. |
| Grep text index | M | Research/personal/homelab "search my notes"; bridges toward RAG. |
| Minimal web Control UI | M | OpenClaw Control UI parity; enterprise dashboards; homelab. |
| Session recall (full-text search over past sessions) | M | Hermes `session_search` parity; research reproducibility; personal journal search. |
| `code_lint`/`code_format`/`code_test` wrappers | M | Developer.md test/CI triage flow. |
| Project instructions file | S-M | Per-worktree `AGENTS.md`-style context; claude-code `CLAUDE.md` parity. |

## Tier 3 - roadmap phases (large)

- Swarm: `/agent` personas, `delegate` tool, auditor agents, generate > check > correct
- Fleet orchestration: supervisor running scoped `replio serve` instances
- Sandboxed exec (namespace/container isolation for `run_command`)
- Notebook mode, interactive data analysis (CSV/SQL), hybrid RAG with vector store
- Plugin ecosystem: PyPI entry-point source, marketplace, per-plugin venv isolation, externalize bundled plugins
- Enterprise plugins: RBAC, connectors (MQTT/OPC-UA/Modbus), durable workflows, hash-chained audit, edge buffering, observability

## Execution order

Each task follows the AGENTS.md doc conventions: build, add `unittest` tests, mark `[x]` in `TODO.md`, log under a new version section at the top of `CHANGELOG.md`, and sync the `pyproject.toml` version.

1. Tier 1 (remaining): Session export to Markdown -> Config validation -> Multi-line input -> Word-level streaming buffering
2. Tier 2 (after Tier 1, order to be re-ranked against the backlog at that point)
3. Tier 3 roadmap phases, one phase at a time, docs-first
