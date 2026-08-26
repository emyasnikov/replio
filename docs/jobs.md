# Scheduled and durable jobs

`replio jobs` turns the one-shot agent loop into a durable workflow engine. A job is a named task run on a schedule, retried with backoff, recorded with a human-in-the-loop status model, and stored as a file so it survives daemon restarts. `replio run` is a single turn. A job is that turn plus scheduling, retries, approvals, and an append-only run history.

## Job store

Jobs live in `.replio/jobs.json` next to the sessions, one register per worktree (same rule as personas). The file is plain JSON and the last writer wins, so run one scheduler per `.replio`. Removing a job removes only its definition - its sessions stay as the append-only log of every run. The register keeps the most recent 100 runs; the full transcript always stays in the session file.

```json
{
  "jobs": [
    {
      "name": "nightly_report",
      "schedule": { "cron": "0 2 * * *" },
      "prompt": "Summarize today's operations logs into a short report.",
      "session": "",
      "mode": "plan",
      "persona": "researcher",
      "system_prompt": "",
      "retries": 3,
      "backoff": 60,
      "timeout": 0,
      "max_context": 0,
      "require_approval": false,
      "task_file": "jobs/nightly_report.md",
      "enabled": true,
      "status": "approved",
      "created_at": "2026-08-26T08:00:00+00:00",
      "next_run_at": "2026-08-27T02:00:00+00:00",
      "last_run_at": "",
      "history": []
    }
  ]
}
```

## Status model

A job is a human-gated workflow, not a blind timer:

```text
proposed > approved > executing > verified | failed
```

`waiting_approval` is the parked state used by `require_approval` jobs (see below).

- `add` creates a `proposed` job. It does not run until it is approved.
- `approve` marks it `approved`; `reject` sends it back to `proposed` and disables it.
- The scheduler or a manual `run` sets it to `executing`, then to `verified` on success (`ok` or `truncated` turn) or `failed` after retries are exhausted.
- `enable` / `disable` / `stop` toggle the `enabled` gate independently. A job runs only when it is `enabled` and its status is `approved`, `verified`, or `failed`. A manual `run` acts as an approval: a successful `proposed` job becomes `verified` and is then scheduled normally.

Every run (each retry attempt included) is appended to the job's `history` with start/finish times, status, reason, duration, session, the assistant output (capped), and the attempt number. The register is saved after each attempt, so a daemon killed mid-retry leaves a correct trail and the next start can pick up.

## Schedules

A job has exactly one schedule:

- **cron** - a 5-field expression `minute hour dom month dow`. Fields support `*`, `*/step`, `a-b`, `a-b/step`, and `a,b,c` lists. `dow` accepts `0` (Sunday) through `7` (also Sunday). The two day fields are restrictive: both must match (unlike some cron variants, a restricted `dom` and `dow` do not OR together). The parser is stdlib-only and deterministic; `next run` is always computed strictly after the previous run, so a scheduler that is down does not catch up on missed windows.
- **interval** - seconds between runs, minimum 60. The `next run` is `interval` seconds after the previous run finishes.
- **at** - a one-shot ISO datetime (e.g. `2026-08-27T02:00:00Z`). After it runs, the job disables itself.

## Job task file

A job is defined by its task, not by a one-line prompt. Use `--file` to link a Markdown task file that describes what has to be done:

```bash
replio jobs add nightly --file jobs/nightly-report.md --cron "0 2 * * *"
```

- **`--prompt` becomes optional** - `--file` alone is enough (at least one of `--prompt` / `--file` is required). If both are given, `--prompt` is the short per-run trigger on top of the task file.
- The default path when `--file` is omitted from the job's own default is `.replio/jobs/<name>.md`; if the file does not exist at `add` time it is **created from a template** (`# <name>` / `## Task` / `## Done when` / `## Notes`) for you to fill in.
- The job stores the path and **stays linked**: the file is re-read at the start of every run, so editing the `.md` is how you change the job - no re-adding, no restart needed.
- **`replio jobs edit <name>`** (also `/jobs edit <name>`) opens the job's task file in `$EDITOR` (creating the template first if needed). `replio jobs show <name>` prints the stored path.
- Paths under the worktree are stored relative to it; absolute paths stay absolute. A missing task file at run time fails that run with a clear `task file not found` reason so a broken link is never silently ignored.

At run time the system prompt is composed as: `persona.system_prompt` (if a persona is set), the task file contents (`## Job task`), `--system-prompt`, and the run memory (`## Run memory`, below); the engine's mode instruction is appended last. With none of persona / task file / custom prompt / memory set, a generic recurring-job prompt is used.

## Run memory

Every run is summarized and the summary is kept as the job's rolling memory, so the next run knows what happened before without a growing session file:

- After each run (successful or failed) the scheduler summarizes the run through the same compaction path as `/compact` (seeded with the previous memory so context carries), and writes the result to **`.replio/jobs/<name>.memory.md`** (atomic write; if the summarize call fails, a short fallback of `Run <ts>: verified|failed` plus the first part of the output or error is stored instead).
- The memory file is **injected into the next run** as the `## Run memory` system prompt block. It is a compact, bounded record - never the whole history.
- `replio jobs show <name>` prints the memory file path and a preview; you can read or hand-edit the `.memory.md` like the task file (the next run will use whatever is there). A memory file that stops being summarized simply stays stale - it never breaks a run.

## CLI reference

```bash
replio jobs list                                # table of jobs and next runs
replio jobs status                              # runtime summary (fired count, last error, uptime)
replio jobs show <name>                         # definition + full run history
replio jobs add <name> --cron "0 2 * * *" --prompt "..." [options]
replio jobs add <name> --interval 3600 --file jobs/<name>.md [options]
replio jobs add <name> --at 2026-08-27T02:00:00Z --prompt "..." [options]
replio jobs approve <name>                      # proposed -> approved (or arm the next run)
replio jobs reject <name>                       # proposed, disabled
replio jobs enable <name> / disable <name>      # toggle the enabled gate
replio jobs stop <name>                         # same as disable - stop it now
replio jobs edit <name>                         # open/ create the task file in $EDITOR
replio jobs remove <name>                       # definition only; sessions stay
replio jobs run <name> [--no-retry] [--verbose] # run now, apply retries, print result
replio jobs daemon [--tick 15] [--quiet]        # scheduler loop, Ctrl-C to stop
```

`replio jobs status` is the journalctl-style runtime view: per job it shows state, how many times it fired (ok/failed), the last error, the next run, uptime since creation, and for `require_approval` jobs whether the next run is approved or waiting.

`add` options:

| Flag | Meaning |
|------|---------|
| `--prompt` | Optional short per-run trigger; required only when `--file` is not given |
| `--file` | Markdown task file describing the job (default `.replio/jobs/<name>.md`, template-created if missing). Linked - edits apply on the next run |
| `--cron` / `--interval` / `--at` | Exactly one schedule (required) |
| `--session` | Stable session name; default is a fresh per-run `job_<ts>_<name>` file |
| `--mode` | Mode override (`plan`, `build`, or custom) |
| `--provider` / `--model` | Provider / model overrides |
| `--persona` | Apply a persona's system prompt, model, and tool permissions |
| `--system-prompt` | System prompt describing the job; without it or a persona, a generic recurring-job prompt is used |
| `--tools-deny NAME` | Deny a tool (repeatable) |
| `--tool-permission category=action` | Permission override, e.g. `bash=allow` (repeatable) |
| `--retries N` | Retries after a failed attempt; default `3` |
| `--backoff SECONDS` | Base backoff, doubled per retry; default `60` |
| `--timeout SECONDS` | Max seconds for one attempt; `0` (default) = no cap |
| `--max-context N` | Auto-compact the session when the provider context exceeds N messages (`0` = never) |
| `--require-approval` | Arm only one run per approve - every run parks in `waiting_approval` until a human approves it |
| `--approval auto` | Start `approved` instead of `proposed` |

The same surface is available in the REPL as `/jobs` (list, status, show, add, approve, reject, enable, disable, stop, remove, run).

## Human in the loop

There are three distinct gates, from coarsest to finest:

1. **Arm / disarm (before any run)** - `add` starts `proposed`; `approve` arms it once, `stop`/`disable` disarms it. This is the baseline gate everyone uses.
2. **Per-run approval (`--require-approval`)** - the gate you want when "something has to be decided" about *this* run, not just arm-or-disarm for all time. Each run parks in `waiting_approval`: the daemon will not fire it, `replio jobs status` shows `WAITING for approve`, and `replio jobs approve <name>` (or `/jobs approve`) arms exactly the next run. After the run finishes it parks again. `reject` clears the grant; `run` still overrides and executes now.
3. **Mid-run blocking approval (tool-level, planned)** - an `ask` tool inside a running job pauses the run in place and waits for a human reply before resuming on the same session. This is the deepest "decide during the task" model and is tracked separately in [TODO.md](../../TODO.md): it needs resumable mid-run state, a wait loop inside the run, and a transport to deliver the ask and return the answer (the planned webhook/email/Telegram connectors drive the same operator API).

A job runs with `HeadlessUI(auto='deny')` - the same posture as `replio serve`. That means as long as mid-run blocking is not implemented, an `ask` tool inside a run is denied, not paused: the run continues without it (or fails if the task depended on it). Give a job the permissions it needs up front (`--tool-permission bash=allow`, a persona carve, or a `--tools-deny` list) and it will not need mid-run interruption.

`timeout` runs the attempt on a daemon thread and abandons it if it overruns. The abandoned thread may still write to the shared session, so a timed-out job should be inspected with `replio jobs show <name>` before a manual retry.

## Session files per run

The **compact memory** is the run-memory file ([Run memory](#run-memory)): a rolling summary that is injected into every run and keeps the model oriented no matter how many runs have happened. Session files are the per-run audit:

- **By default each run gets a fresh session file**: `job_<YYYYMMDD>_<HHMMSS>_<name>.json` (e.g. `job_20260826_110230_nightly_report.json`), distinct from interactive sessions (`ses_...`) and delegation sub-agents (`sub_...`). No single file grows forever; every run is a complete, self-contained log. A same-second collision is resolved with a `_2` suffix. Retries within one run share that run's file (the retry sees the failed attempt's context).
- **`--session <name>` opts into a stable, growing session** instead - useful when you want one continuous transcript.
- `--max-context N` still bounds an exceptionally long single run: before a run the scheduler summarizes older history and trims the provider context (the append-only file is untouched).
- The job register keeps the most recent 100 runs, each recording its session file.

## How a run executes

Each attempt builds a fresh headless `Engine` from the job's overrides, using the run's session file (fresh `job_<ts>_<name>`, or the `--session` override), and calls `chat()` once. The system prompt is composed from the persona (if set), the linked task file (`## Job task`), `--system-prompt`, and the rolling run memory (`## Run memory`); with none of them a generic recurring-job prompt is layered in, telling the model this is a recurring job with earlier context. After the run finishes, the run is summarized into `.replio/jobs/<name>.memory.md` for the next run, so continuity lives in the memory file rather than in a growing session. A retry continues from the failed attempt's trail (same run's session file) with a "Previous attempt failed. Retry this job" header. `replio jobs run --verbose` streams the live turn (tokens to stdout, tool activity to stderr) before the summary; `replio jobs run` prints the final answer headlessly.

## Scheduling semantics

The daemon (`replio jobs daemon`) wakes on the `--tick` interval (default 15s), runs every due, runnable job sequentially, and sleeps. Jobs are single-threaded: one at a time, in name order. Concurrent execution is future work. `next_run_at` is the single source of truth - it is computed when a job is added and after each run, and a `next_run_at` in the past makes a job due immediately. A missed window is not backlogged: after any run the next run is recomputed strictly after the current time (or the run's finish for interval schedules), so a scheduler stopped overnight runs the current schedule on wake instead of replaying old ones.

## Session logs

Each run writes a complete append-only log at `.replio/sessions/job_<ts>_<name>.json` (or the `--session` override): user prompts, assistant answers, tool calls and results, thinking, errors, and the `permissions` audit array. That is the durable record a `verified` or `failed` status points to. `replio jobs show <name>` prints the run history and each run's session file plus the last output; `/session export job_<ts>_<name>` renders one run's transcript to Markdown.