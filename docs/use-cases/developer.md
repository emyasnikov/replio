# Developer teams & coding assistants

Replio is a terminal-native agent core, so developers are the most natural first audience. Repo-scoped agents, permission-gated machine tools, and a headless CLI slot it into a working day and a CI pipeline without a new editor, daemon, or dependency tree. The shared foundation is in [index.md](index.md).

## Why it fits

- **Right tool, already installed** - a stdlib-only Python package and a REPL you already understand. No lockfile churn, no supply-chain surface to audit.
- **Scoped by repository** - launch inside a repo (or pass `--path`) and the worktree scoping in [docs/tools.md](../tools.md) keeps file tools inside it. `file_read`, `list_dir`, `glob`, `grep`, and `file_write` operate on the code you are actually working on.
- **CI-native** - `replio run` is a single headless command with `--output json`, so agents run in pipelines, pre-commit hooks, and scheduled jobs the same way they run in the terminal.
- **Permission discipline by design** - `run_command` (builds, tests, git) defaults to `ask`, so the model proposes before it executes. Headless agents auto-deny anything unapproved, which makes accidental shell side effects rare.

## Fit by use case

- **Codebase Q&A** - "where is the retry logic?", "how do providers register?" answered from the actual tree via `glob`/`grep`/`file_read`, with the file and line cited.
- **PR and change review** - summarize diffs, flag risks, and draft review comments. Sessions give the whole review thread a replayable record.
- **Test and CI triage** - `replio run -p "explain this test failure" --output json` in the pipeline, with the tool results (exit codes, logs) feeding the analysis.
- **Documentation generation** - draft release notes, README sections, and migration guides from history and code, then `file_write` them under review.
- **Multi-repo fleets** - one `replio serve --path <repo>` agent per repository, answering over the API. See [docs/fleet.md](../fleet.md).
- **Release and ops notes** - summarize changelogs, craft commit messages, and prepare runbooks from local records.

## Hands-on setup

A complete step-by-step recipe - a lead/implementer/tester/reviewer fleet on a Raspberry Pi with cloud Ollama (`gpt-oss:20b-cloud`), git worktree isolation, and human gates between every hand-off - is in [docs/usage/programming.md](../usage/programming.md).

## Gaps and planned

Plan/Build modes are live: `/mode plan` (or `replio run --mode plan`) switches to a read-only posture where write and exec tools are denied and the model is instructed to plan, `/mode build` restores full access, and custom modes can express other postures. Swarm foundations are live too: a persona catalog (bundled defaults plus global/local `.replio/personas.json`), an in-process sub-agent engine, and the `delegate` tool that runs a task under a persona and returns its answer - so a single REPL can hand research, writing, or programming work to `researcher`/`programmer`/`code-reviewer` sub-agents (`/persona`, `/tool delegate`, see [docs/personas.md](../personas.md) and [docs/swarm.md](../swarm.md)). Developer workflow tooling is live: `file_edit` for surgical search-and-replace, read-only `git` plus gated `git_commit`, `code_test`/`code_lint`/`code_format` wrappers, a `run_command` command allowlist (`tool_permission.bash_allow`), and the per-worktree instructions file (`project_instructions`, default `AGENTS.md`) auto-loaded into the system prompt. The interactive `/agent` command and auditor agents (generate > check > correct) are planned. Notebook mode for iterating on code cells and richer interactive data analysis are still planned. These track the roadmap in [PLAN.md](../../PLAN.md) and [TODO.md](../../TODO.md). Tab completion, `/compact`, `/session`, and `replio run` already cover most day-to-day flows.

## Get started

1. `pip install replio` and run `replio` inside your repository. `/connect` to your provider or point `--base-url` at a company gateway.
2. Try `/tool` to run tools directly, then ask a codebase question and watch it read the tree.
3. For automation, `replio run -p "summarize the failing tests" --path tests --output json` - add it to CI with `--yes` only when you are comfortable with the permissions.
4. Scope harder agents with `tools.deny` (a read-only reviewer denies `run_command` and `file_write`) and `tool_permission` categories in [docs/config.md](../config.md).
