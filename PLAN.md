# Replio - Execution Plan

Groups the next tasks into work packages, each providing a distinct next-level capability. Packages are ordered top-to-bottom by urgency and importance, low-effort core hardening first, through capability growth, to the larger platform and enterprise goals. Re-rank the packages against the backlog before starting each next step (docs-first for the roadmap phases). Task detail lives in `TODO.md`; shipped changes are in `CHANGELOG.md` under the matching version.

Sourced from the use-case gap (`docs/use-cases/`), competitor parity (`docs/vs/`), or TODO items.

## Method

- Effort: S < M < L
- Provides: the capability the task delivers

## REPL polish

Finished REPL hardening first: multi-line input, word-level streaming buffering. Remaining:

| Task | Effort | Provides |
|------|--------|----------|
| Surface soft tool results as dimmed info lines | S | `(empty file)`, `(no matches)` notes visible in the REPL |

## Developer workflow

Repo-aware coding assistance: version control, lint/format/test wrappers, scoped shell policy, per-worktree context.

| Task | Effort | Provides |
|------|--------|----------|
| `git` tool | M | status/diff/commit from the loop |
| `code_lint`/`code_format`/`code_test` wrappers | M | test/CI triage flow |
| `run_command` command allowlist | S-M | chain-aware startswith policy over `&&`/`||`/`;`/`|`/`&`, no shell scripts (`tool_permission.bash_allow`) |
| Project instructions file | S-M | per-worktree AGENTS.md context |
| Workspace sessions | M | scoped `--workspace` dir, optional git sync |

## Knowledge & memory

Answers drawn from past sessions and local documents, bridging toward a vector store.

| Task | Effort | Provides |
|------|--------|----------|
| Session recall | M | full-text search over past sessions |
| Grep text index | M | "search my notes" in the worktree |
| `docs_search` | M | local grep + DuckDuckGo doc lookups |
| Hybrid RAG + vector store | L | local semantic search |
| Topic-aware ranking | M | intent-weighted search results |
| Citations / source attribution | S-M | URL + snippet with every answer |

## Share & polish

Session artifacts become portable and navigable.

| Task | Effort | Provides |
|------|--------|----------|
| Conversation sharing links | M | web-shareable sessions (builds on Markdown export) |
| Session import from Markdown/JSON | M | round-trip session exchange |
| Bookmarks (`/bookmark`) | S | session pinning |
| Command palette / fuzzy history | M | CTRL-P style history search |

## Interactive analysis & notebooks

Data work inside the loop.

| Task | Effort | Provides |
|------|--------|----------|
| Interactive data analysis | M | CSV querying, SQL execution |
| Notebook mode | L | persistent editable cells with run outputs |

## Plugin ecosystem

Capabilities install as discoverable, isolated packages.

| Task | Effort | Provides |
|------|--------|----------|
| PyPI plugin source | M | install from `importlib.metadata` entry points |
| Plugin registry / marketplace | M-L | discoverable plugin sharing |
| Per-plugin virtualenv isolation | M | strongest dependency separation |
| Externalize bundled plugins | M | versioned repos, bundled copies stay the default |
| Plugin test harness | S-M | plugins ship a test suite, `replio plugins test <name>` runs it |
| Cross-plugin tool router | M | virtual `open`/`search` dispatch by argument |
| Web scraper + PDF-to-text plugins | S-M | non-text content types |
| Agent folder watcher | S-M | process new files on arrival |

## Multi-agent swarm

Agents cooperate through personas, delegation, and review loops.

| Task | Effort | Provides |
|------|--------|----------|
| `/agent` personas | M | per-agent prompt, session, model |
| Custom system prompts per session | S-M | per-site instructions, groundwork for personas |
| Per-agent permission profiles | M | per-agent `tool_permission` |
| `delegate` tool | M | sub-agent loop returning a result |
| Auditor agents + generate/check/correct | M | review-and-fix loops |
| PM/dev/tester team orchestration | M | user-facing team pattern |

## Fleet & control plane

Run many scoped agents under a supervisor with a control surface.

| Task | Effort | Provides |
|------|--------|----------|
| `/spawn` command | S-M | launch a scoped `replio serve` agent from the REPL (home -> project path), supervise and delegate to it |
| Fleet orchestration | L | supervisor: ports, health, restart, config gen |
| Immutable agent config | S-M | served agents cannot change their own config |
| Minimal web Control UI | M | dashboard over the JSON API |
| Multiuser API + queue / rate limits | M | concurrent feeds without blocking the loop |
| Headless web API plugin-first | S-M | FastAPI via the dependency plugin |
| Observability + telemetry decision | M | latency/cost/error metrics; Pi-style contracts |

## Remote channels

Command agents from messaging apps.

| Task | Effort | Provides |
|------|--------|----------|
| Channel gateway | M | one adapter surface over the engine/serve API |
| Telegram adapter | S-M | long-polling bot, send + receive |
| WhatsApp adapter | M | business-API HTTP channel |
| More adapters (Discord, Signal, email) | S-M | extra channels as plugins |
| Remote auth + session scoping + headless deny | M | secure remote command of an agent |

## Enterprise operations & data

Durable, auditable workflows over plant and business data.

| Task | Effort | Provides |
|------|--------|----------|
| Durable / scheduled jobs | L | cron-style runs, retries, human-in-the-loop status model |
| Hash-chained audit log | M | tamper-evident additive log |
| Edge / offline store-and-forward | M | buffering for unreliable connectivity |
| Sandboxed exec | L | namespace/container isolation for `run_command` |
| Tool dry-run mode | S-M | propose args/effects without executing |
| Connectors (`read_stream`/`write_stream`) | M-L | MQTT, OPC-UA, Modbus data channels |
| Time-series, inference, optimisation tools | M | anomaly/forecast, `model_infer`, scheduling |
| SCADA control + reporting | M | registers, Markdown/PDF/BI push |
| Onboarding wizard, RBAC, queue scaling | M | MES/data-source setup, roles, concurrency |

## Release & community

Distribution and outward-facing presence.

| Task | Effort | Provides |
|------|--------|----------|
| `replio update` | M | self-update |
| Standalone binary build | M | single executable |
| Docs site | S-M | ReadTheDocs + GitHub Pages |
| Community channels | S | Discord/X slots in README |
| Naming/positioning + competitor research | S | validated USP and name decision |
