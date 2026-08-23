# Replio - Execution Plan

Groups the next tasks into work packages, each providing a distinct next-level capability. Packages are ordered top-to-bottom by urgency and importance, low-effort core hardening first, through capability growth, to the larger platform and enterprise goals. Re-rank the packages against the backlog before starting each next step (docs-first for the roadmap phases). Task detail lives in `TODO.md`; shipped changes are in `CHANGELOG.md` under the matching version.

## Method

- Effort: S < M < L
- Provides: the capability the task delivers
- Source: the use-case gap (`docs/use-cases/`), competitor parity (`docs/vs/`), or TODO item it answers

## REPL polish

Finished REPL hardening first: multi-line input, word-level streaming buffering. Remaining:

| Task | Effort | Provides | Source |
|------|--------|----------|--------|
| Surface soft tool results as dimmed info lines | S | `(empty file)`, `(no matches)` notes visible in the REPL | TODO |

## Developer workflow

Repo-aware coding assistance: version control, lint/format/test wrappers, scoped shell policy, per-worktree context.

| Task | Effort | Provides | Source |
|------|--------|----------|--------|
| `git` tool | M | status/diff/commit from the loop | Developer use case; claude-code/opencode parity |
| `code_lint`/`code_format`/`code_test` wrappers | M | test/CI triage flow | Developer use case |
| `run_command` command allowlist | S-M | safe-shell policy (`tool_permission.bash_allow`), all-or-none removed | Developer use case; security |
| Project instructions file | S-M | per-worktree AGENTS.md context | claude-code `CLAUDE.md` parity |
| Workspace sessions | M | scoped `--workspace` dir, optional git sync | TODO |

## Knowledge & memory

Answers drawn from past sessions and local documents, bridging toward a vector store.

| Task | Effort | Provides | Source |
|------|--------|----------|--------|
| Session recall | M | full-text search over past sessions | Hermes `session_search` parity |
| Grep text index | M | "search my notes" in the worktree | Research/personal/homelab use cases |
| `docs_search` | M | local grep + DuckDuckGo doc lookups | TODO |
| Hybrid RAG + vector store | L | local semantic search | TODO |
| Topic-aware ranking | M | intent-weighted search results | TODO |
| Citations / source attribution | S-M | URL + snippet with every answer | Research use case |

## Share & polish

Session artifacts become portable and navigable.

| Task | Effort | Provides | Source |
|------|--------|----------|--------|
| Conversation sharing links | M | web-shareable sessions (builds on Markdown export) | OpenCode `/share` |
| Session import from Markdown/JSON | M | round-trip session exchange | TODO |
| Bookmarks (`/bookmark`) | S | session pinning | TODO |
| Command palette / fuzzy history | M | CTRL-P style history search | TODO |

## Interactive analysis & notebooks

Data work inside the loop.

| Task | Effort | Provides | Source |
|------|--------|----------|--------|
| Interactive data analysis | M | CSV querying, SQL execution | TODO |
| Notebook mode | L | persistent editable cells with run outputs | TODO |

## Plugin ecosystem

Capabilities install as discoverable, isolated packages.

| Task | Effort | Provides | Source |
|------|--------|----------|--------|
| PyPI plugin source | M | install from `importlib.metadata` entry points | TODO |
| Plugin registry / marketplace | M-L | discoverable plugin sharing | OpenClaw clawhub parity |
| Per-plugin virtualenv isolation | M | strongest dependency separation | TODO |
| Externalize bundled plugins | M | versioned repos, bundled copies stay the default | TODO |
| Cross-plugin tool router | M | virtual `open`/`search` dispatch by argument | TODO |
| Web scraper + PDF-to-text plugins | S-M | non-text content types | TODO |
| Agent folder watcher | S-M | process new files on arrival | TODO |

## Multi-agent swarm

Agents cooperate through personas, delegation, and review loops.

| Task | Effort | Provides | Source |
|------|--------|----------|--------|
| `/agent` personas | M | per-agent prompt, session, model | `docs/swarm.md` |
| Custom system prompts per session | S-M | per-site instructions, groundwork for personas | TODO |
| Per-agent permission profiles | M | per-agent `tool_permission` | TODO |
| `delegate` tool | M | sub-agent loop returning a result | `docs/swarm.md` |
| Auditor agents + generate/check/correct | M | review-and-fix loops | TODO |
| PM/dev/tester team orchestration | M | user-facing team pattern | TODO |

## Fleet & control plane

Run many scoped agents under a supervisor with a control surface.

| Task | Effort | Provides | Source |
|------|--------|----------|--------|
| Fleet orchestration | L | supervisor: ports, health, restart, config gen | `docs/fleet.md` |
| Immutable agent config | S-M | served agents cannot change their own config | Enterprise control-plane rule |
| Minimal web Control UI | M | dashboard over the JSON API | OpenClaw Control UI parity |
| Multiuser API + queue / rate limits | M | concurrent feeds without blocking the loop | TODO |
| Headless web API plugin-first | S-M | FastAPI via the dependency plugin | TODO |
| Observability + telemetry decision | M | latency/cost/error metrics; Pi-style contracts | Enterprise; Pi parity |

## Enterprise operations & data

Durable, auditable workflows over plant and business data.

| Task | Effort | Provides | Source |
|------|--------|----------|--------|
| Durable / scheduled jobs | L | cron-style runs, retries, human-in-the-loop status model | Enterprise |
| Hash-chained audit log | M | tamper-evident additive log | Enterprise |
| Edge / offline store-and-forward | M | buffering for unreliable connectivity | Enterprise |
| Sandboxed exec | L | namespace/container isolation for `run_command` | Security |
| Tool dry-run mode | S-M | propose args/effects without executing | Enterprise tool gateway |
| Connectors (`read_stream`/`write_stream`) | M-L | MQTT, OPC-UA, Modbus data channels | Enterprise |
| Time-series, inference, optimisation tools | M | anomaly/forecast, `model_infer`, scheduling | Enterprise plugin list |
| SCADA control + reporting | M | registers, Markdown/PDF/BI push | Enterprise plugin list |
| Onboarding wizard, RBAC, queue scaling | M | MES/data-source setup, roles, concurrency | Enterprise plugin list |

## Release & community

Distribution and outward-facing presence.

| Task | Effort | Provides | Source |
|------|--------|----------|--------|
| `replio update` | M | self-update | Pi `pi update --self` parity |
| Standalone binary build | M | single executable | TODO |
| Docs site | S-M | ReadTheDocs + GitHub Pages | TODO |
| Community channels | S | Discord/X slots in README | TODO |
| Naming/positioning + competitor research | S | validated USP and name decision | TODO / `docs/vs/` |