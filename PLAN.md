# Execution Plan

Groups the next tasks from `TODO.md` (`## Open`) into work packages, each providing a distinct next-level capability. Packages are ordered top-to-bottom by urgency and importance, low-effort core hardening first, through capability growth, to the larger platform and enterprise goals. Re-rank the packages against the backlog before starting each next step (docs-first for the roadmap phases).

Finished tasks are removed from this file - they live as one-liners in `TODO.md` `## Done` and in detail under the matching version in `CHANGELOG.md`. `VISION.md` holds the why (vision, decisions, architecture). This file holds the what. The roles and sync rules of all four planning files are in `AGENTS.md`.

Sourced from the use-case gap (`docs/use-cases/`), competitor parity (`docs/vs/`), or TODO items.

## Method

- Effort: S < M < L
- Provides: the capability the task delivers
- Milestones: the swarm/team track (M1-M3) groups its tasks into verifiable phases

## Milestones - swarm and team track

The current priority: one terminal, whole teams (`VISION.md`). Stages run sequentially via `run_subagent`. The composition machinery (templates, recipes, generator, library) lives in a movable private plugin, never in the core.

### Skeleton and core hooks

- [ ] `Engine.run_team` - sequential stage loop: brief builder, `run_subagent`, handoff, team memory write
- [ ] Kit skeleton - `plugins/replio-teamkit/`: manifest, entry module, one template, one recipe, tests
- [ ] `docs/teamkit.md` draft - authoring + move-out guide

Verified: `/team run` end-to-end + unit tests (mock provider, no network).

### Authoring and template matching

- [ ] Template-based composition - stack signature from request + project description -> tags -> matching templates -> AI-generated deltas only
- [ ] Team kit library - flat tagged store (stack, customer, project-type), importable into new projects
- [ ] `/teamkit` authoring commands - init, list, new, match, export, import, per-customer split
- [ ] Auto team selection - lead agent composes the team for a task and delegates in sequence
- [ ] `/agent` personas - interactive persona selection/run UX
- [ ] Docs completed (`docs/teamkit.md` full)

Verified: one command composes a new project's team. A second project reuses stored artifacts.

### Reuse, scheduling, move-out

- [ ] Persistent member sessions for recurring teams (`job`-style warm sessions, one-off runs stay fresh)
- [ ] `jobs add --team` - scheduled team runs via the jobs daemon
- [ ] Reuse verified across two projects
- [ ] Kit moved out per the `docs/teamkit.md` checklist - own/per-customer repo, `plugins install --global`, bundled copy removed from the default plugin set

Verified: full workflow with the kit installed externally.

## How the layers compose

One round hands off in three steps:

1. **Start** - the operator starts a task: `replio jobs add`/`run` for scheduled work, or a REPL prompt for ad-hoc work. The jobs operator API adds a remote start (`POST /jobs/<name>/approve`) later
2. **Distribute + review** - the lead agent splits the task into subtasks and delegates them: sequentially by persona today (`delegate` tool, team stages next), routed to fleet agents over `POST /chat` once team/job configs land, with auditor agents reviewing the output (generate > check > correct)
3. **Return** - results come back to the operator: the delegate result or job summary today, the jobs operator API + webhook/email/Telegram connectors when the jobs layer lands. The fleet supervisor restarts crashed processes underneath. The jobs layer restarts failed work - two kinds of restart, both compose

Fleet is the substrate that stays up, not the conductor of the work.

## Tool engineering for agents

Tools are the provider-facing surface - one OpenAI-compatible contract, registry metadata drives the loop. Hardening it for any provider (weak OpenAI-compatible backends especially), from the Anthropic tool-writing principles (choosing the right tools, namespacing, meaningful context, token efficiency, description prompt-engineering) and the tool-use evaluation methodology.

| Task | Effort | Provides |
|------|--------|----------|
| Tool spec polish (P5) - `grep.glob` -> `include`, description examples / preference guidance | S | unambiguous parameters and clearer tool selection |

## Team orchestration (swarm core)

Agents cooperate through personas, delegation, and team stages. Sub-agents use the caller's provider, plugin manager, and worktree (see `docs/swarm.md`).

| Task | Effort | Provides |
|------|--------|----------|
| Plugin contribution hooks (M1) | S | plugin-owned personas/teams/skills without forking the core |
| Skills registry (M1) | S-M | persona `skills` resolved and injected into sub-agent system prompts |
| Teams registry (M1) | S-M | named team configurations ("writing" = researcher > writer > referencer > editor, "programming" = planner > programmer > tester > code-reviewer) with ordering + handoff - subsumes the TODO "Jobs registry - named team configurations" item |
| Sequential team runs (M1) - `Engine.run_team` | M | stage-by-stage delegation with generated briefs, shared team memory (`.replio/teams/<name>/memory.md`), handoff |
| Auto team selection (M2) | M | the lead agent composes the team (personas + order + briefs) for a task |
| `/agent` personas (M2) | M | interactive persona selection/run UX (registry + sub-engine + delegate landed) |
| Custom system prompts per session | S-M | per-site instructions |
| Auditor agents + generate > check > correct orchestration | M-L | review-and-fix loops (later milestone, listed in VISION.md out-of-scope) |
| PM/dev/tester team orchestration as a user-facing pattern | M | team pattern on top of the teams registry (lands with M1/M2) |
| Delegation progress in the REPL + interactive delegation focus | M | live status of the running member, jump into its log, arrows switch views |
| Swarm orchestration umbrella (TODO item) | - | decomposed by this package: `/agent` personas, auditor agents, generate > check > correct, team patterns |

## Team kit plugin (private, movable)

Templates, recipes, library, and generator - the composition machinery, kept out of the core so internal know-how leaves the repo as one documented unit. Bundled during development as `plugins/replio-teamkit/`, moved out via the `docs/teamkit.md` checklist (M3).

| Task | Effort | Provides |
|------|--------|----------|
| Kit skeleton (M1) - `src/plugin.py`, `templates/`, `recipes/`, `library/`, `tests/` | M | installable private kit |
| Template-based composition (M2) - stack signature -> tags -> matching templates -> AI-generated deltas only (`chat_nonstreaming`), persisted locally (personas.json + skills + teams.json, with reload) | M | fresh team per project, reusing proven artifacts |
| Team kit library (M2) - flat tagged store per stack and customer | M | reuse across projects without publishing know-how |
| `/teamkit` authoring commands (M2) - init, list, new, match, export, import, per-customer split | M | quick team definition per customer |
| Move-out (M3) - external repo (optionally per-customer), `plugins install --global`, bundled copy removed from the default set | S-M | the kit fully outside the project |
| Plugin download service for battle-tested kits | L | later milestone, listed in VISION.md out-of-scope |

## Jobs operations layer

React to and see jobs from outside the box. Run teams on schedule.

| Task | Effort | Provides |
|------|--------|----------|
| `jobs add --team` (M3) - scheduled team runs, per-run team summary session, member sessions as team stages | M | recurring team pipelines |
| Jobs operator API - `GET /jobs` and `POST /jobs/<name>/approve` (also `reject`/`run`/`disable`) on `replio serve` | M | any client can see/act per agent |
| Job event hooks - the scheduler emits typed transitions (`proposed`, `approved`, `will_run`, `executing`, `verified`, `failed`, `timeout`, `waiting_approval`) to registered `services`, channel-agnostic core | M | notification source |
| Job connectors - bundled `replio-core-webhook` (stdlib JSON POST, zero deps) first, email (SMTP + polling) and Telegram (urllib long-poll) plugins later, all driving the jobs operator API | M-L | operators react in time |
| Fleet jobs overview - `replio jobs list --root <dir>` combined agent/job table (agent, job, status, next run, task), then a web Control UI on top | M | one view of what runs next |
| Mid-run blocking job approval - an `ask` tool inside a running job pauses the run in place (per-tool-call `waiting_approval`), notifies via a connector, and resumes the same session when the operator replies, needs resumable mid-run state, a wait loop inside the run, and the connectors/transport above | L | "decide during the task" |

## Fleet & control plane

Run many scoped agents under a supervisor with a control surface.

| Task | Effort | Provides |
|------|--------|----------|
| `/spawn` command | S-M | launch a scoped `replio serve` agent from the REPL (home -> project path), supervise and delegate to it |
| Immutable agent config | S-M | served agents cannot change their own config |
| Minimal web Control UI | M | dashboard over the JSON API |
| Multiuser API + queue / rate limits | M | concurrent feeds without blocking the loop |
| Headless web API plugin-first | S-M | FastAPI via the dependency plugin |
| Observability + telemetry decision | M | latency/cost/error metrics, Pi-style contracts |

## Developer workflow

Repo-aware coding assistance: version control, lint/format/test wrappers, scoped shell policy, per-worktree context.

| Task | Effort | Provides |
|------|--------|----------|
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
| Plugin contribution hooks (M1) | S | personas/teams/skills from plugins |
| PyPI plugin source | M | install from `importlib.metadata` entry points |
| Plugin registry / marketplace | M-L | discoverable plugin sharing |
| Shared plugin virtualenv | M | one venv for all plugin dependencies |
| Per-plugin virtualenv isolation | M | strongest dependency separation |
| Externalize bundled plugins | M | versioned repos, bundled copies stay the default |
| Externalize bundled providers - `opencode`/`opencode-go` (then the vendor providers) move to bundled plugins via the existing `register_providers` hook. `BaseProvider`/`OpenAICompatibleProvider`, the `PROVIDERS` dict, `detect_provider`, and engine resolution stay core. Needs a base_url hostname-hint mechanism so plugin providers auto-detect in `/connect` | M | core stays the substrate, gateway/vendor providers version independently |
| Plugin test harness | S-M | plugins ship a test suite, `replio plugins test <name>` runs it |
| Cross-plugin tool router | M | virtual `open`/`search` dispatch by argument |
| Web scraper + PDF-to-text plugins | S-M | non-text content types |
| Agent folder watcher | S-M | process new files on arrival |

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
| Docs site (ReadTheDocs) | S-M | ReadTheDocs reference docs |
| Community channels | S | Discord/X slots in README |
| Naming/positioning + competitor research | S | validated USP and name decision |
