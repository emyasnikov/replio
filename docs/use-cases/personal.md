# Personal & private use

Replio's local-first, zero-dependency design makes it a natural private assistant: your data on your machine, no telemetry, no cloud account. Sessions are complete append-only logs, so a personal agent doubles as a searchable journal of what you asked, what it did, and what it found. The shared foundation - what Replio provides today, the adoption path, and the reference architecture - is in [index.md](index.md).

## Why it fits

- **Privacy by default** - config and sessions live on your disk, provider traffic is outbound, and no external service holds your data. Pair with a local model (Ollama via `/connect`) and nothing sensitive leaves the machine.
- **No account, no subscription** - `pip install`, connect a provider, and run. No SaaS tenant, no per-seat pricing, no vendor lock-in.
- **Low footprint** - a single agent is a few MB, so it runs comfortably on a laptop, a small server, or a Raspberry Pi.
- **A journal that keeps itself** - every conversation is persisted with timestamps, duration, and tool activity. A personal agent is a self-documenting research and decision log.

## Fit by use case

- **Personal knowledge assistant** - point an agent at a notes or documents folder (`replio serve --path notes`) and ask questions in plain language. `glob`, `grep`, `read_file`, and `list_dir` keep answers grounded in your own files, with the matching excerpts cited.
- **Research assistant** - `web_search`, `open`, and `fetch_page` gather current information with sources. Sessions preserve the full research trail: queries, pages fetched, and reasoning.
- **Notes and journaling** - a daily or topic-scoped session is a structured log. `/session load` and `/session save` switch between threads, and `/compact` trims provider context without touching the stored log.
- **Life and home automation** - with `run_command` you can drive scripts and local tools. Keep it read-only at first (reporting, summaries, reminders). Anything that writes or executes belongs behind the `ask` confirmation that `bash` carries by default.
- **Offline and intermittent use** - local models and a stdlib core need no external service, so the agent keeps working on a train, in the field, or on a disconnected machine.

## Gaps and planned

Personal power-user features are planned, not current: bookmarks (`/bookmark`), interactive data analysis and SQL over local files, notebook mode, hybrid local search with embeddings (vector store), and richer search over notes. These track the roadmap in [TODO.md](../../TODO.md). For most personal use the current core is already complete.

## Get started

1. `pip install replio`, then `replio` for the REPL or `replio serve --path ~/notes` for a headless agent.
2. `/connect` to a provider - Ollama for a fully local setup, or any OpenAI-compatible endpoint for hosted models.
3. Set permissions to taste: `tool_permission.web: allow`, `tool_permission.bash: ask` (the default), and use `tools.deny` to remove capabilities you do not want (for example `write_file` on a research-only agent).
4. Ask away. Every turn lands in `.replio/sessions/` as a complete, replayable log.
