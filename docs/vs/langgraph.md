# Replio vs. LangGraph

This document compares **Replio** (github.com/emyasnikov/replio) and **LangGraph** (github.com/langchain-ai/langgraph), the low-level orchestration framework and runtime from LangChain. They are not direct substitutes - Replio is a ready-to-run agent application, while LangGraph is a library you embed to build your own stateful agent. Both are MIT-licensed Python, but they target different layers of the stack.

## Project Overview

| Project | Primary Language | Repo | License | Core Focus |
|---------|------------------|------|---------|------------|
| Replio | Python (stdlib only) | https://github.com/emyasnikov/replio | MIT | Lightweight REPL + CLI + HTTP API with zero external dependencies |
| LangGraph | Python + TypeScript/JS | https://github.com/langchain-ai/langgraph | MIT | Low-level orchestration framework and runtime for long-running, stateful agents |

## Architecture & Runtime Model

| Feature | Replio | LangGraph |
|---------|--------|-----------|
| What it is | An application - a terminal REPL/CLI/HTTP agent core | A library - a graph-based orchestration runtime you embed in your own app |
| Core model | Single streaming agent loop per turn | `StateGraph` of nodes/edges mixing deterministic and agentic steps |
| Entry point | `replio` (REPL), `replio run`, `replio serve` | You write code - `graph.invoke(...)` from your application |
| Dependencies | None beyond stdlib | External deps (LangChain, checkpointer DBs), and inspired by Pregel, Apache Beam, and NetworkX |
| Deployment | Local process, or `replio serve` HTTP API | Embedded in your service, or deployed via LangGraph Platform/LangSmith |

Replio gives you a working agent out of the box. LangGraph gives you fine-grained control to build bespoke agents - you design the graph, choose persistence, and wire in models and tools yourself.

## Tooling & Function Calling

| Aspect | Replio | LangGraph |
|--------|--------|-----------|
| Built-in tools | Web search, fetch page, file I/O, shell - via bundled plugin tools | None built-in, you connect models and tools yourself |
| Tool organization | Plugin registry | LangChain component integrations (models, tools, retrievers) |
| Function-calling scheme | OpenAI-compatible JSON schema | Model-independent, works with any tool-calling model |
| Refinement/planning | Generic query refinement via tool metadata | Prebuilt agent loops in higher-level LangChain, or the graph gives full control |

## Persistence, Durability & Memory

| Feature | Replio | LangGraph |
|---------|--------|-----------|
| Session persistence | Append-only JSON session logs | Pluggable checkpointer (e.g. Postgres, SQLite) for durable, resumable state |
| Long-running agents | Turn-based, one loop per turn | Built for long-running agents that persist through failures and resume |
| Memory | Per-session context only | Short-term working state plus cross-session memory stores |
| Human-in-the-loop | Confirm prompts for tools | `interrupt`/resume for human oversight at any graph node |

## Channels & UI

| Feature | Replio | LangGraph |
|---------|--------|-----------|
| Built-in UI | Terminal REPL | None (headless library) |
| Web/API | `replio serve` HTTP JSON API | You build your own API/UI on top |
| Streaming | Streaming output to the REPL | Streaming support as part of the runtime |
| Observability | Session logs | LangSmith tracing, evaluation, and monitoring |

## Provider & Model Support

| Aspect | Replio | LangGraph |
|--------|--------|-----------|
| LLM providers | Ollama (default), OpenAI, Groq, Anthropic, any OpenAI-compatible endpoint | Model-agnostic via LangChain integrations (OpenAI, Anthropic, Google, local, and more) |
| Local models | Via Ollama | Via local model integrations |

## Community & Ecosystem

| Project | License | Community | Ecosystem | Docs |
|---------|---------|-----------|-----------|------|
| Replio | MIT | Small, GitHub-centric | Python plugins | Docs in repo, minimal |
| LangGraph | MIT | Large LangChain ecosystem | LangChain, LangSmith, LangGraph Platform, Deep Agents harness | docs.langchain.com, extensive |

Used in production by companies including Klarna, Uber, and J.P. Morgan.

## When to Choose Which

| Scenario | Recommended Project | Why |
|----------|---------------------|-----|
| You want a working terminal agent or HTTP API with zero setup | Replio | Ready to run, stdlib only |
| You are building a bespoke, long-running, stateful agent or workflow as an app feature | LangGraph | Graph orchestration, durable execution, human-in-the-loop |
| You need a minimal embeddable agent core with append-only logs | Replio | Simple turn-based loop + session log |

## Summary Table

| Feature | Replio | LangGraph |
|---------|--------|-----------|
| Type | Application (REPL/CLI/HTTP) | Framework/library |
| Language | Python (stdlib) | Python + TypeScript |
| Orchestration | Fixed agent loop | Custom graph (deterministic + agentic) |
| Persistence | JSON session logs | Durable checkpoints + memory |
| Human-in-the-loop | Tool confirm prompts | Graph interrupts |
| UI | Terminal REPL + HTTP API | None (you build it) |
| Use case | Turn-key terminal agent | Building custom stateful agents |

## References

- https://docs.langchain.com
- https://github.com/emyasnikov/replio
- https://github.com/emyasnikov/replio/tree/main/docs
- https://github.com/langchain-ai/langgraph
