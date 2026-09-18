# Execution Plan

Groups the next tasks from `TODO.md` (`## Open`) into work packages, each providing a distinct next-level capability. Packages are ordered top-to-bottom by urgency and importance, vision-first. Re-rank the packages against the backlog before starting each next step (docs-first for the roadmap phases).

Finished tasks are removed from this file and live as one-liners in `TODO.md` `## Done` and in detail under the matching version in `CHANGELOG.md`.

## Method

- Effort: S < M < L
- Provides: the capability the task delivers

## Runs, focus, and memory

A session belongs to a run. Whoever starts a run creates its session: the root at startup, `delegate`/`team` at delegation, the scheduler per job run. A role is an identity a run borrows (prompt, skills, carve), never a session owner, so there is no `agent_<role>` and no `sub_<key>`.

`/focus` is a navigator over the run tree. It never creates a session, it makes the existing runs visible and marks the current one, and it lets the operator jump into another by `#run`, `#session_id`, `session:name`, `parent`, `child`, `sibling`, `next`, `prev`, or `back`. A delegated agent runs blocking and hidden behind a status line, and the operator may jump in to print its output instead of waiting for the result.

`handoff` is run-to-run control, not session management. An agent that is done or paused hands the focus to another existing run, whose session is preserved so it continues where it stopped. Handoff never creates or names a session.

Continuity has two scales. Within a run, the run's own session is the context, so a planner giving a developer another task only adds the new task and the developer still knows its recent work. Across runs, continuity is bounded memory: a compacted Markdown summary per role, team, and job, injected into briefs and refreshed after runs, so recurring work does not replay an ever-growing session.

Decisions: remove `agent_<role>` and `sub_<key>` (every session is ordinary, owned by its run), focus only attaches, handoff only moves focus, a caller may resume or compact/drop a run's context, memory is automatic and configurable per role/team/job plus a manual memorize, and live runs are the enabling step for watching or joining an agent.

| Task | Effort | Provides |
|------|--------|----------|
| Provider session binding - bind the provider session id to the run's session | S | cache and context reuse across switches |
| Sync architecture, swarm, session, and command docs - align the behavior docs with run-owned sessions and bounded memory | S | aligned reference docs |

Step order: provider session binding, then sync the architecture, swarm, session, and command docs.

## Non-blocking runs & live focus

Deferred until the run-owned corrections above land. Each piece is independent, and the status animation needs no threads, so it can land first.

| Task | Effort | Provides |
|------|--------|----------|
| Run status animation - a Braille spinner and status line for long delegation and team stages, no threads required | S | visible progress |
| Per-run output buffers - buffer each run's streamed output and route input to the focused run | M | per-run logs and input |
| Background execution - run sub-agents and teams off the calling thread, with thread-safe session and registry access | L | non-blocking runs |
| Live focus and cancellation - watch or join a running run and cancel it | M | watch or join a running agent |

## Assistant roles & team orchestration

The assistant is the operator's entry point. A composer turns a task into a team, a manager runs teams, and specialists do the work. A role keeps a standing identity and extends it with skills per task, teams iterate generate > check > correct, and focus follows the call tree of runs. This track resumes after the runs, focus, and memory redesign above, ordered by dependency.

| Task | Effort | Provides |
|------|--------|----------|
| Manager role - runs one or many teams and reports, sequential first | M | one window over several teams |
| Core dev team configuration - a development team with the review loop plus the project lead/support teams and skills | S | ready-made teams and skills |
| Role-name sync - adopt assistant, composer, manager, and specialist across types, prompts, and docs | S | one canonical vocabulary |
| Assistant-roles track docs - record the architecture and work packages in VISION, PLAN, and TODO | S | documented direction |

## Control & governance

The assistant is the operator's single window to the machine: served agents are spawned and supervised from the REPL, unattended runs park their asks instead of failing, and finished work reports back. This is the control surface the rest of the roadmap builds on.

| Task | Effort | Provides |
|------|--------|----------|
| Onboarding - first run: the assistant introduces itself, explains what it can do, and asks what to do. No system-level configuration for simple users | M | a supported first step |
| One-window status - `/status` lists sessions, running agents, and configured jobs on the machine, with logs reachable from the same surface | M | see everything from one place |
| Agent health monitoring - the assistant watches endpoints (e.g. the `/health` of agents running as web APIs) and warns when an agent stops responding | S-M | alert when an agent is down |
| `/spawn` command - launch a scoped `replio serve` agent from the REPL (home -> project path), supervise (health/list/stop) and delegate to it | S-M | fleet agents from the terminal |

## Delegation & swarm

Agents cooperate through types, delegation, and team stages. Sub-agents use the caller's provider, plugin manager, and worktree (see `docs/swarm.md`).

| Task | Effort | Provides |
|------|--------|----------|
| Per-agent todo lists - view a delegated agent's tasks, mark items done, jump into its session, and ask for the current state (OpenCode-style) | M | current state of a delegation |
| Auto team selection - the assistant composes the team (types + order + briefs) for a task and delegates in sequence | M | team orchestration as a user-facing pattern |
| `/agent` types - interactive type selection/run UX (type registry, sub-engine, and `delegate` landed) | M | pick a type and run with it |
| Auditor agents + generate > check > correct orchestration - run a main agent, an auditor, and a fix pass in a loop until passing | M-L | review-and-fix loops (later phase, listed in VISION.md out-of-scope) |
| PM/dev/tester team orchestration as a user-facing pattern | M | team pattern on top of the teams registry |
| Custom system prompts per session | S-M | per-site instructions |
| Agent type directory scan for export/import - read `.replio/types/*.md` (front-matter types) to import and export types to Markdown | S-M | portable type definitions |
| Swarm orchestration umbrella (TODO item) | - | decomposed by this package |

## Jobs operations + report-back

React to and see jobs from outside the box. Run teams on schedule.

| Task | Effort | Provides |
|------|--------|----------|
| Recurring tasks carry their own role - each job carries its own type and skills, so behavior like "make doc changes per AGENTS.md" is encoded once instead of re-prompted every time | S-M | encoded recurring behavior |
| `jobs add --team` - scheduled team runs, per-run team summary session, member sessions as team stages | M | recurring team pipelines |
| Jobs operator API - `GET /jobs` and `POST /jobs/<name>/approve|reject|run|disable` on `replio serve` | M | any client can see/act per agent |
| Job event hooks - the scheduler emits typed transitions (`proposed`, `approved`, `will_run`, `executing`, `verified`, `failed`, `timeout`, `waiting_approval`) to registered `services`, channel-agnostic core | M | notification source |
| Job connectors - bundled `replio-core-webhook` (stdlib JSON POST, zero deps) first, email (SMTP + polling) and Telegram (urllib long-poll) plugins later, all driving the jobs operator API | M-L | operators react in time |
| Fleet jobs overview - `replio jobs list --root <dir>` combined agent/job table (agent, job, status, next run, task), then a web Control UI on top | M | one view of what runs next |
| Mid-run blocking job approval - an `ask` inside a running job pauses in place (per-tool-call `waiting_approval`), notifies via a connector, and resumes the same session on reply. Needs resumable mid-run state, a wait loop inside the run, and the connectors above | L | decide during the task |

## Tool engineering for agents

Tools are the provider-facing surface: one OpenAI-compatible contract, registry metadata drives the loop. Hardening it for any provider (weak OpenAI-compatible backends especially), from the Anthropic tool-writing principles (choosing the right tools, namespacing, meaningful context, token efficiency, description prompt-engineering) and the tool-use evaluation methodology.

| Task | Effort | Provides |
|------|--------|----------|
| Tool spec polish - `grep.glob` -> `include`, description examples / preference guidance | S | unambiguous parameters and clearer tool selection |
| Full `file_*` namespace extension - if `file_glob`/`file_grep` prove better with most models, extend the prefix to `list_dir`/`glob`/`grep` (old names stay aliases) | S-M | consistent namespace |

## Fleet & control plane

Run many scoped agents under a supervisor with a control surface.

| Task | Effort | Provides |
|------|--------|----------|
| Immutable agent config - `replio serve` agents cannot change their own configuration, permissions, or tool list | S-M | control-plane rule |
| Minimal web Control UI - stdlib `http.server` page over the existing `replio serve` JSON API | M | dashboard over the JSON API |
| Multiuser API + queue / rate limits | M | concurrent feeds without blocking the loop |
| Headless web API plugin-first - stdlib `http.server` fallback, richer framework (FastAPI) via the dependency plugin | S-M | fast API without core deps |
| Observability + telemetry decision - latency/cost/error metrics, Pi-style contracts | M | measured operations |

## Plugin ecosystem

Capabilities install as discoverable, isolated packages.

| Task | Effort | Provides |
|------|--------|----------|
| PyPI plugin source - install from `importlib.metadata` entry points | M | regular-package plugins |
| Plugin registry / marketplace - discoverable plugin sharing | M-L | plugin discovery |
| Shared plugin virtualenv - one venv for all plugin dependencies | M | isolated deps, one venv |
| Per-plugin virtualenv isolation - per-plugin `.venv`, site-packages injected at import | M | strongest dependency separation |
| Externalize bundled plugins - versioned repos, bundled copies stay the default | M | versioned bundled plugins |
| Plugin test harness - external plugins ship a test suite, `replio plugins test <name>` runs it | S-M | tested plugins |
| Cross-plugin tool router - virtual tool names (`open`, `search`, ...) dispatch per-argument to the matching plugin handler | M | context-aware dispatch |
| Web scraper + PDF-to-text plugins | S-M | non-text content types |
| Agent folder watcher - process new files on arrival | S-M | arrival-driven work |

## Developer workflow

Repo-aware coding assistance: version control, lint/format/test wrappers, scoped shell policy, per-worktree context.

| Task | Effort | Provides |
|------|--------|----------|
| Workspace sessions - tools write into a scoped `--workspace` dir, optional git sync | M | scoped workspaces |
| `code_debug` / `compile` - pdb/gcc/rustc wrappers (test/lint/format landed as `code_test`/`code_lint`/`code_format`) | S-M | debug + compile |

## Knowledge & memory

Answers drawn from past sessions and local documents, bridging toward a vector store.

| Task | Effort | Provides |
|------|--------|----------|
| Session recall - full-text search over past sessions | M | answer from own history |
| Grep text index - internal bundled plugin (stdlib) indexing converted text files | M | search my notes in the worktree |
| `docs_search` - local grep + DuckDuckGo doc lookups | M | documentation lookups |
| Hybrid RAG + vector store | L | local semantic search |
| Topic-aware ranking - classifier for query intent to weight search results | M | intent-weighted results |
| Citations / source attribution - URL + snippet with every answer | S-M | grounded answers |

## Remote channels

Command agents from messaging apps.

| Task | Effort | Provides |
|------|--------|----------|
| Channel gateway - one adapter surface over the engine/serve API | M | one adapter surface |
| Telegram adapter - long-polling bot, send + receive | S-M | Telegram channel |
| WhatsApp adapter - business-API HTTP channel | M | WhatsApp channel |
| More adapters (Discord, Signal, email) | S-M | extra channels as plugins |
| Remote auth + session scoping + headless deny | M | secure remote command |

## Interactive analysis & notebooks

Data work inside the loop.

| Task | Effort | Provides |
|------|--------|----------|
| Interactive data analysis - CSV querying, SQL execution | M | data work in the loop |
| Notebook mode - persistent editable cells with run outputs | L | iterative data work |

## Share & polish

Session artifacts become portable and navigable.

| Task | Effort | Provides |
|------|--------|----------|
| Conversation sharing links - web-shareable sessions (builds on Markdown export) | M | shareable sessions |
| Session import from Markdown/JSON | M | round-trip session exchange |
| Bookmarks (`/bookmark`) | S | session pinning |
| Command palette / fuzzy history - CTRL-P style history search | M | fast history search |

## Enterprise operations & data

Durable, auditable workflows over plant and business data.

| Task | Effort | Provides |
|------|--------|----------|
| Hash-chained audit log | M | tamper-evident additive log |
| Edge / offline store-and-forward | M | buffering for unreliable connectivity |
| Sandboxed exec - namespace/container isolation for `run_command` | L | safe shell |
| Tool dry-run mode - propose args/effects without executing | S-M | safe tool gateway |
| Connectors (`read_stream`/`write_stream`) - MQTT, OPC-UA, Modbus data channels | M-L | industrial data channels |
| Time-series, inference, optimisation tools - anomaly/forecast, `model_infer`, scheduling | M | plant analytics |
| SCADA control + reporting - registers, Markdown/PDF/BI push | M | plant control + reporting |
| Onboarding wizard, RBAC, queue scaling - MES/data-source setup, roles, concurrency | M | enterprise readiness |

## Release & community

Distribution and outward-facing presence.

| Task | Effort | Provides |
|------|--------|----------|
| `replio update` | M | self-update |
| Standalone binary build | M | single executable |
| Docs site (ReadTheDocs) | S-M | ReadTheDocs reference docs |
| Community channels - Discord/X slots in README | S | community presence |
| Naming/positioning + competitor research | S | validated USP and name decision |

## How the layers compose

One round hands off in three steps:

1. **Start** - the operator starts a task: `replio jobs add`/`run` for scheduled work, or a REPL prompt or `/tool delegate` for ad-hoc work. The jobs operator API adds a remote start (`POST /jobs/<name>/approve`) later
2. **Distribute + review** - the assistant splits the task into subtasks and delegates them: sequentially by type or team stage today (`delegate`, `Engine.run_team`), routed to fleet agents over `POST /chat` once cross-process delegation lands, with auditor agents reviewing the output (generate > check > correct)
3. **Return** - results come back to the operator: the delegate result, team memory, or job summary today, the jobs operator API + webhook/email/Telegram connectors when the jobs layer lands. The fleet supervisor restarts crashed processes underneath. The jobs layer restarts failed work - two kinds of restart, both compose

Fleet is the substrate that stays up, not the conductor of the work.
