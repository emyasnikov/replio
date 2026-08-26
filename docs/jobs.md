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

## CLI reference

```bash
replio jobs list                                # table of jobs and next runs
replio jobs status                              # runtime summary (fired count, last error, uptime)
replio jobs show <name>                         # definition + full run history
replio jobs add <name> --cron "0 2 * * *" --prompt "..." [options]
replio jobs add <name> --interval 3600 --prompt "..." [options]
replio jobs add <name> --at 2026-08-27T02:00:00Z --prompt "..." [options]
replio jobs approve <name>                      # proposed -> approved (or arm the next run)
replio jobs reject <name>                       # proposed, disabled
replio jobs enable <name> / disable <name>      # toggle the enabled gate
replio jobs stop <name>                         # same as disable - stop it now
replio jobs remove <name>                       # definition only; sessions stay
replio jobs run <name> [--no-retry] [--verbose] # run now, apply retries, print result
replio jobs daemon [--tick 15] [--quiet]        # scheduler loop, Ctrl-C to stop
```

`replio jobs status` is the journalctl-style runtime view: per job it shows state, how many times it fired (ok/failed), the last error, the next run, uptime since creation, and for `require_approval` jobs whether the next run is approved or waiting.

`add` options:

| Flag | Meaning |
|------|---------|
| `--prompt` | The task prompt sent on every run (required) |
| `--cron` / `--interval` / `--at` | Exactly one schedule (required) |
| `--session` | Session name; default `job.<name>` |
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

## Memory across runs and the session file

**Yes, all runs of one job share a single session file** - `.replio/sessions/job.<name>.json` (default `job.<name>`; override with `--session`). That is deliberate: it is the job's memory. Every run is appended to the same append-only log, so the next run starts with the full context of earlier ones - files already produced, mistakes made, what the last run did. The model never re-discovers prior state (the common failure mode of stateless cron jobs).

Two consequences to know about:

- **The file grows, by design.** Sessions are complete audit logs and are never rewritten (compaction only trims what the model *sees*). A job you are testing (like a `testXXX.txt` writer) will grow its session fast. Keep it, read `/session export job.<name>` or `replio jobs show <name>` for the summary, and use `--max-context` to bound the model's view.
- **Context needs to be bounded, or the model drowns.** Pass `--max-context N`: before each run the scheduler summarizes the older history into a compact summary and trims the provider context to the recent messages (the append-only file is untouched, the audit survives). Without it, provider context grows with the file until it hits window limits. The job register itself keeps only the most recent 100 runs.

## How a run executes

Each attempt builds a fresh headless `Engine` from the job's overrides, loads the job's stable session (`job.<name>` by default), and calls `chat()` once. When no `--system-prompt` or `--persona` is set, a generic recurring-job prompt is injected that tells the model this is a recurring job with earlier runs in its history - so it stays consistent and does not redo completed work. Because the session is stable, `--max-context` aside, later runs carry the context of earlier ones, and a retry continues from the failed attempt's trail with a "Previous attempt failed. Retry this job" header. `replio jobs run --verbose` streams the live turn (tokens to stdout, tool activity to stderr) before the summary; `replio jobs run` prints the final answer headlessly.

## Scheduling semantics

The daemon (`replio jobs daemon`) wakes on the `--tick` interval (default 15s), runs every due, runnable job sequentially, and sleeps. Jobs are single-threaded: one at a time, in name order. Concurrent execution is future work. `next_run_at` is the single source of truth - it is computed when a job is added and after each run, and a `next_run_at` in the past makes a job due immediately. A missed window is not backlogged: after any run the next run is recomputed strictly after the current time (or the run's finish for interval schedules), so a scheduler stopped overnight runs the current schedule on wake instead of replaying old ones.

## Session logs

Each job writes to `.replio/sessions/job.<name>.json`, a complete append-only log of every run: user prompts, assistant answers, tool calls and results, thinking, errors, and the `permissions` audit array. That is the durable record a `verified` or `failed` status points to. `replio jobs show <name>` prints the matching run history and the last output; `/session export job.<name>` renders the transcript to Markdown.