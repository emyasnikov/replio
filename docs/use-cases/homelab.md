# Home lab, makers & self-hosters

For home-lab operators, the appeal is the same as everywhere else but sharper: a few-megabyte, stdlib-only agent that runs on a Raspberry Pi or a spare NUC, keeps its data local, has no telemetry, and composes with the rest of your stack over a plain HTTP API. The shared foundation is in [index.md](index.md).

## Why it fits

- **Fits the hardware you have** - a couple of MB per process, no JVM, no node_modules. It idles happily on a Pi next to your DNS server and uses a fraction of the RAM of a browser tab.
- **Self-hosted and sovereign** - sessions and config are files on your disk. Point it at Ollama on the same box and the whole stack is yours, offline-capable, with no vendor in the loop.
- **Scriptable and composable** - `replio run` in cron, `replio serve` behind your reverse proxy, agents talking to each other over `POST /chat`. It slots into an existing automation stack instead of demanding its own platform.
- **Permission-gated by design** - home automation touches real systems, so the `ask` gate on `run_command` and worktree scoping keep the agent proposing before it acts.

## Fit by use case

- **Personal dashboards and reports** - scheduled `replio run` jobs summarize logs, sensor readings, service health, and monthly usage into short reports on your own schedule.
- **Home automation assistance** - explain device status and logs, draft automation rules, and propose changes. Keep writes and exec behind the `ask` confirmation.
- **Self-hosted knowledge base** - a docs or notes agent scoped to a folder answers from your files with `grep`/`read_file` grounded citations.
- **Service-watch agent** - a per-service agent (`replio serve --path /srv/<app>`) triages logs and outage notes over the API. See [docs/fleet.md](../fleet.md) for the fleet pattern.
- **Off-grid and lab bench** - a laptop or Pi with a local model works without connectivity, so the agent goes where the network does not.

## Gaps and planned

Home-lab power-user features are planned: bookmarks, notebook mode, RAG/vector search over your documents, and MCP support to wire the agent into other self-hosted tools. These track the roadmap in [TODO.md](../../TODO.md). The current core already covers reporting, triage, and grounded Q&A.

## Get started

1. `pip install replio` on the Pi or NUC, and run `replio` in a terminal (or `replio serve --path /srv/notes --port 8787` behind your proxy).
2. `/connect` to Ollama on the same machine for a fully local setup, or any OpenAI-compatible endpoint.
3. Lock it down: `tool_permission.bash: ask`, and use `tools.deny` to strip capabilities you do not want on a given agent.
4. Schedule `replio run -p "summarize today's logs" --output json` in cron, and let sessions accumulate as your searchable operations log.
