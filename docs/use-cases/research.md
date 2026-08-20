# Research & academia

Research work is built on traceable, reproducible steps, and unpublished results can be commercially or legally sensitive. Replio's local-first storage and complete session logs match both requirements: the data and the reasoning stay on your machine, and every query, source, and conclusion is reconstructable afterward. The shared foundation is in [index.md](index.md).

## Why it fits

- **Confidentiality for unpublished work** - config and sessions live on your disk, and a local model (Ollama via `/connect`) keeps everything on premises. Grants, embargoes, and pre-publication data never touch a third-party service.
- **A reproducible research trail** - every session persists the question, the sources fetched, the tool calls, and the reasoning. That is a literature-search log, a data-analysis notebook, and a citation trail all in one.
- **Grounded answers with sources** - `web_search` / `open` / `fetch_page` pull current literature and surface the sources. File tools keep the model answering from your own corpus (papers, notes, lab exports) rather than from memory.
- **No IT approval needed** - a stdlib Python package installs anywhere and runs headless, so a lab or a single researcher can adopt it without a managed environment.

## Fit by use case

- **Literature review** - search, fetch, and summarize papers and preprints, with the trail saved per session. `/session save litreview-<topic>` keeps topics as separate threads.
- **Corpus queries** - point an agent at a folder of papers or notes (`replio serve --path ~/papers`) and ask comparative questions, with `grep`/`read_file` grounding every answer in the actual text.
- **Data analysis support** - describe datasets and plan analyses in plain language, draft analysis code and experiment notes, and prepare results summaries. Keep execution behind `run_command`'s `ask` gate.
- **Writing support** - draft methods, related-work, and appendix text from the corpus with citations attached, then `write_file` for review.
- **Lab notebooks and logs** - sessions double as a structured, timestamped lab notebook per project or experiment.

## Gaps and planned

Deep research features are planned: local RAG with embeddings and vector store for semantic search over your corpus, interactive CSV/SQL data analysis, and notebook mode. These track the roadmap in [TODO.md](../../TODO.md). Until then, `grep`-based full-text search over a converted corpus covers most needs.

## Get started

1. `pip install replio`, then run `replio` (or `replio serve --path ~/papers` for a headless corpus agent).
2. `/connect` to a provider - prefer a local model for embargoed or export-controlled material.
3. Scope permissions: `tool_permission.bash: ask`, `tools.deny` anything unused, and keep write tools out of read-only review agents.
4. Start a session per topic. The complete log under `.replio/sessions/` is your reproducibility record.
