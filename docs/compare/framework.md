# Framework

A **framework** gives you building blocks to construct an agent: you write the control flow, choose the persistence, and wire in models and tools yourself. A **harness** has the loop already built in, so you bring a model and instructions and press go. Replio is a harness, so this page is less a head-to-head and more a choice of layer: build on a framework when you need custom orchestration inside your own application, and use a harness when you want a working agent.

Frameworks are a good fit when the agent is one feature of a larger product, when you need a bespoke graph or pipeline, or when you must embed the runtime in an existing service. They are a poor fit when you want a ready terminal, CLI, or HTTP agent with scheduling and delegation out of the box.

## Replio's position

Replio is the opposite trade. It ships the loop, tools, permissions, sessions, delegation, teams, jobs, and a fleet supervisor as a runnable application, so there is nothing to build before the first run. The price is less control over the exact orchestration: the loop is fixed, and customization happens through tools, types, skills, teams, and plugins rather than by rewriting the control flow.

## Representatives

| Project | Language | License | Model | Primary focus |
|---------|----------|---------|-------|---------------|
| AutoGen | Python, .NET | Open source | Conversable agents | Multi-agent conversation and code execution |
| CrewAI | Python | MIT | Role-based crews | Role-playing agent teams and tasks |
| LangChain | Python, TypeScript | MIT | Chains and components | Combining LLM calls, tools, and data |
| LangGraph | Python, TypeScript | MIT | Stateful graph | Long-running, durable, stateful agents |
| LlamaIndex | Python, TypeScript | MIT | Data and indexes | RAG and data-centric LLM apps |
| Microsoft Agent Framework | Python, .NET | Open source | Agents and workflows | Enterprise agent SDK merging AutoGen and Semantic Kernel |
| Replio | Python (stdlib only) | MIT | Ready harness | Runnable agent core with orchestration |

`Replio` is a harness listed for contrast. The rest are frameworks you build on.

## Profiles

### AutoGen
A Microsoft-originated framework for multi-agent conversations, where agents talk to each other and can execute code. It is a strong fit for research and complex multi-agent dialogue inside your own application. Replio instead runs a fixed loop with delegation and teams as configuration.

### CrewAI
A Python framework for role-based agent teams, where each agent has a role, goal, and backstory and executes tasks. It leans on the crew metaphor. Replio's teams are ordered pipelines with per-stage skills and a shared memory file, run from a ready harness.

### LangChain
A broad framework for composing LLM calls, tools, retrievers, and memory, with a large integration surface. It is a toolkit, not a runtime. Replio avoids the dependency surface and ships only the standard library.

### LangGraph
LangChain's low-level orchestration runtime built on a state graph, with durable checkpointers, interrupts for human-in-the-loop, and long-running execution. It offers fine-grained control that Replio deliberately does not expose.

### LlamaIndex
A data framework for connecting LLMs to data, with indexes, retrievers, and RAG pipelines. It is the tool for retrieval-heavy applications. Replio has no built-in RAG and focuses on acting through tools.

### Microsoft Agent Framework
Microsoft's SDK for building agents and workflows, consolidating ideas from AutoGen and Semantic Kernel for Python and .NET. It targets enterprise application integration. Replio targets a self-contained, auditable runtime instead.

## When to choose

| Scenario | Pick | Why |
|----------|------|-----|
| The agent is one feature inside a larger application | A framework | You control the flow and embed the runtime |
| A bespoke graph or non-linear orchestration | LangGraph, LangChain | You design nodes, edges, and persistence |
| Role-based research teams or multi-agent dialogue | CrewAI, AutoGen | Purpose-built multi-agent abstractions |
| Retrieval and data-centric pipelines | LlamaIndex | Indexes, retrievers, and RAG |
| A working terminal, CLI, or HTTP agent with no build step | Replio | Harness ships the loop, tools, and orchestration |

## Sources and evidence

Replio facts come from this repository. Framework facts come from each project's public documentation and repository, summarized at a level intended to stay stable. No performance or resource numbers are claimed here.

## References

- https://github.com/crewAIInc/crewAI
- https://github.com/emyasnikov/replio
- https://github.com/langchain-ai/langchain
- https://github.com/langchain-ai/langgraph
- https://github.com/microsoft/agent-framework
- https://github.com/microsoft/autogen
- https://github.com/run-llama/llama_index
