# Scheduled and durable jobs

`replio jobs` turns the one-shot agent loop into a durable workflow engine. A job is a named prompt run on a schedule, retried with backoff, recorded with a human-in-the-loop status model, and stored as a file so it survives daemon restarts. `replio run` is a single turn. A job is that turn plus scheduling, retries, approvals, and an append-only run history.

## Job store

Jobs live in `.replio/jobs.json` next to the sessions, one register per worktree (same rule as personas). The file is plain JSON and the last writer wins, so run one scheduler per `.replio`. Removing a job removes only its definition - its sessions stay as the append-only log of every run.

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
      "retries": 3,
      "backoff": 60,
      "timeout": 0,
      "enabled": true,
      "status": "approved",
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

- `add` creates a `proposed` job. It does not run until it is approved.
- `approve` marks it `approved`; `reject` sends it back to `proposed` and disables it.
- The scheduler or a manual `run` sets it to `executing`, then to `verified` on success (`ok` or `truncated` turn) or `failed` after retries are exhausted.
- `enable` / `disable` toggle the `enabled` gate independently. A job runs only when it is `enabled` and its status is `approved`, `verified`, or `failed`. A manual `run` acts as an approval: a successful `proposed` job becomes `verified` and is then scheduled normally.

Every run (each retry attempt included) is appended to the job's `history` with start/finish times, status, reason, duration, session, and attempt number. The register is saved after each attempt, so a daemon killed mid-retry leaves a correct trail and the next start can pick up.

## Schedules

A job has exactly one schedule:

- **cron** - a 5-field expression `minute hour dom month dow`. Fields support `*`, `*/step`, `a-b`, `a-b/step`, and `a,b,c` lists. `dow` accepts `0` (Sunday) through `7` (also Sunday). The two day fields are restrictive: both must match (unlike some cron variants, a restricted `dom` and `dow` do not OR together). The parser is stdlib-only and deterministic; `next run` is always computed strictly after the previous run, so a scheduler that is down does not catch up on missed windows.
- **interval** - seconds between runs, minimum 60. The `next run` is `interval` seconds after the previous run finishes.
- **at** - a one-shot ISO datetime (e.g. `2026-08-27T02:00:00Z`). After it runs, the job disables itself.

## CLI reference

```bash
replio jobs list                                # table of jobs and next runs
replio jobs show <name>                         # definition + full run history
replio jobs add <name> --cron "0 2 * * *" --prompt "..." [options]
replio jobs add <name> --interval 3600 --prompt "..." [options]
replio jobs add <name> --at 2026-08-27T02:00:00Z --prompt "..." [options]
replio jobs approve <name>                      # proposed -> approved
replio jobs reject <name>                       # proposed, disabled
replio jobs enable <name> / disable <name>      # toggle the enabled gate
replio jobs remove <name>                       # definition only
replio jobs run <name> [--no-retry]             # run now, apply retries, print result
replio jobs daemon [--tick 15] [--quiet]        # scheduler loop, Ctrl-C to stop
```

`add` options:

| Flag | Meaning |
|------|---------|
| `--prompt` | The prompt sent on every run (required) |
| `--cron` / `--interval` / `--at` | Exactly one schedule (required) |
| `--session` | Session name; default `job.<name>` |
| `--mode` | Mode override (`plan`, `build`, or custom) |
| `--provider` / `--model` | Provider / model overrides |
| `--persona` | Apply a persona's system prompt, model, and tool permissions |
| `--system-prompt` | System prompt override |
| `--tools-deny NAME` | Deny a tool (repeatable) |
| `--tool-permission category=action` | Permission override, e.g. `bash=allow` (repeatable) |
| `--retries N` | Retries after a failed attempt; default `3` |
| `--backoff SECONDS` | Base backoff, doubled per retry; default `60` |
| `--timeout SECONDS` | Max seconds for one attempt; `0` (default) = no cap |
| `--approval auto` | Start `approved` instead of `proposed` |

The same surface is available in the REPL as `/jobs` (list, show, add, approve, reject, enable, disable, remove, run).

## How a run executes

Each attempt builds a fresh headless `Engine` from the job's overrides, loads the job's stable session (`job.<name>` by default), and calls `chat()` once. Because the session is stable, later runs carry the context of earlier ones, and a retry continues from the failed attempt's trail with a "Previous attempt failed. Retry this job" header. Runs use `HeadlessUI(auto='deny')` - the same posture as `replio serve` - so any `ask`-gated tool is denied outright; a job's reachable surface is exactly its `allow` tools on paths inside the worktree. Manually approving a job and the `--approval auto` option are the human-in-the-loop gates; the daemon alone never approves a proposed job.

`timeout` runs the attempt on a daemon thread and abandons it if it overruns. The abandoned thread may still write to the shared session, so a timed-out job should be inspected with `replio jobs show <name>` before a manual retry.

## Scheduling semantics

The daemon (`replio jobs daemon`) wakes on the `--tick` interval (default 15s), runs every due, runnable job sequentially, and sleeps. Jobs are single-threaded: one at a time, in name order. Concurrent execution is future work. `next_run_at` is the single source of truth - it is computed when a job is added and after each run, and a `next_run_at` in the past makes a job due immediately. A missed window is not backlogged: after any run the next run is recomputed strictly after the current time (or the run's finish for interval schedules), so a scheduler stopped overnight runs the current schedule on wake instead of replaying old ones.

## Session logs

Each job writes to `.replio/sessions/job.<name>.json`, a complete append-only log of every run: user prompts, assistant answers, tool calls and results, thinking, errors, and the `permissions` audit array. That is the durable record a `verified` or `failed` status points to. `replio jobs show <name>` prints the matching run history; `/session export job.<name>` renders the transcript to Markdown.