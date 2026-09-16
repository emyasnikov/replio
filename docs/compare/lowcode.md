# Low-code

A **low-code** tool gives you a visual canvas for building AI or automation flows, and lets you drop into code for the parts that need it. You assemble nodes, connect them, and the platform runs the result, often exposing it as an API. It is the middle ground between a framework (all code) and a no-code product (no code).

Low-code tools win when the flow is integration-heavy, when a visual map helps a team understand it, or when non-programmers need to assemble pieces a developer then extends. They are a poor fit when you want a small auditable runtime, when you prefer everything in code and version control, or when you run on low-resource hardware.

## Replio's position

Replio is code-first: a terminal harness with a fixed agent loop, driven by prompts, slash commands, and configuration files. It has no visual canvas. Its composition model is the registries (types, teams, skills) and the `delegate` and `team` tools, all editable as text and kept in the repository. The trade is a smaller footprint and a fully auditable runtime, at the cost of the visual builder.

The planned PlantUML plugin points the other way: an external plugin that can draw a configuration or a run as a node diagram, borrowing the readability of a canvas without moving the runtime into one.

## Representatives

| Project | Language | License | Building style | Primary focus |
|---------|----------|---------|----------------|---------------|
| Dify | Python + TypeScript | Open source (with commercial restrictions) | Visual workflow canvas | LLM app development and backend-as-a-service |
| Flowise | TypeScript | Open source | Drag-and-drop canvas | LLM apps and chatflows on LangChain |
| Langflow | Python | MIT | Visual flow canvas | Agent, RAG, and MCP app builder |
| n8n | TypeScript | Fair-code (Sustainable Use License) | Node-based workflow editor | Workflow automation with AI agent nodes |
| Replio | Python (stdlib only) | MIT | Code and configuration | Runnable agent harness with orchestration |

`Replio` is a harness listed for contrast. The rest are visual builders.

## Profiles

### Dify
An open-source platform for building LLM applications with a visual workflow editor and a backend-as-a-service layer. It targets teams shipping LLM apps and agents with observability and a managed API. Replio stays a terminal-first core with no platform services.

### Flowise
A drag-and-drop builder for LLM apps and chatflows, built on top of LangChain components. It is approachable for prototyping assistants and RAG chains. Replio trades the canvas for a stdlib-only runtime and built-in jobs, fleet, and delegation.

### Langflow
A visual builder for agents, RAG apps, and MCP servers that generates Python under the hood, from DataStax and now IBM. It offers a large component library and flow-as-API deployment. Replio offers a code-first harness with no external dependencies.

### n8n
A fair-code workflow automation platform with a node editor, 400+ integrations, and AI agent nodes. It is strongest at wiring business systems together. Replio is narrower: a scoped agent core with scheduling and delegation rather than broad app integration.

## When to choose

| Scenario | Pick | Why |
|----------|------|-----|
| A visual flow a mixed team can read and edit | Langflow, n8n, Dify, Flowise | Canvas, prebuilt components, flow-as-API |
| Broad integration with business apps and triggers | n8n | 400+ integrations and templates |
| A small, auditable, code-first agent you version with the project | Replio | Stdlib runtime, text configuration, session logs |
| Running many scoped agents on low-resource hardware | Replio | Minimal footprint and a fleet supervisor |

## Sources and evidence

Replio facts come from this repository. Platform facts come from each project's public documentation and repository, summarized at a level intended to stay stable. No performance or resource numbers are claimed here.

## References

- https://docs.dify.ai
- https://docs.flowiseai.com
- https://docs.langflow.org
- https://docs.n8n.io
- https://github.com/emyasnikov/replio
