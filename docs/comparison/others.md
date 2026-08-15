# Other Personal Assistant / Coding Agent Projects

The personal AI assistant / coding-agent landscape is rapidly evolving. Below is an up-to-date (2026-08) snapshot of notable open-source projects worth exploring if you are looking for alternatives to REPL.io. For detailed side-by-side comparisons, see [OpenClaw](openclaw.md), [OpenCode](opencode.md), and [Pi](pi.md).

> **Tip** - For each project, check the repository for the latest release notes, documentation, and compatibility with your preferred LLM provider.

| # | Project | Repo | Primary Language | Core Focus | Notable Features | Current Status |
|---|---------|------|------------------|------------|------------------|----------------|
| 1 | **Cody** | https://github.com/github/cody | TypeScript | IDE-integrated AI coding assistant | VS Code & JetBrains plugins, on-premise server, GitHub-native integration | Actively maintained, frequent releases |
| 2 | **LangChain** | https://github.com/hwchase17/langchain | Python | Agentic framework | Tool calling, memory, chain building, many APIs | Production-grade, large community |
| 3 | **AutoGen** | https://github.com/microsoft/autogen | Python | Multi-agent orchestration | Agent-to-agent communication, role-based agents, sandboxing | Active, used in Microsoft projects |
| 4 | **OpenAI Agent Toolkit** | https://github.com/openai/agent-toolkit | Python | Tool-calling framework | Agent runtime, sandbox, prompt templates | Early-stage, rapid development |
| 5 | **OpenAI Assistants API** | - | - | Cloud-hosted personal assistant | Multi-step workflows, file handling, webhook integration | Proprietary, but open-source SDKs |
| 6 | **OpenAssistant** | https://github.com/LAION-AI/Open-Assistant | Python | Conversational AI with crowd-sourced training | Multi-modal, large-scale community | Active research project |
| 7 | **Haystack** | https://github.com/deepset-ai/haystack | Python | Retrieval-augmented LLM pipelines | Document loaders, pipelines, UI dashboard | Enterprise-grade, well-documented |
| 8 | **LlamaIndex** (now LlamaStack) | https://github.com/run-llama/llama-index | Python | Retrieval-augmented generation | Vector stores, data connectors, agentic workflows | Robust, production-ready |
| 9 | **LocalAI** | https://github.com/localai/localai | Go | LLM deployment & orchestration | Model serving, API gateway, plugin SDK | Production-grade, cloud-agnostic |
| 10 | **KoboldAI** | https://github.com/koboldai/koboldai | Python | Local LLM playground | Web UI, CLI, remote API, multi-model support | Active community, frequent updates |
| 11 | **OpenCode** | https://github.com/anomalyco/opencode | TS/JS | Full-stack AI coding agent | Terminal UI, desktop app, multi-agent workflow | Actively maintained, large plugin ecosystem |
| 12 | **Pi** | https://github.com/earendil-works/pi | TS/JS | Monorepo with agent core | Unified LLM API, telemetry, TUI | Active, frequent releases |
| 13 | **OpenClaw** | https://github.com/openclaw/openclaw | TS/JS | Multi-channel personal assistant | Gateway, UI, channel adapters (Slack, Discord, etc.) | Actively maintained, expanding ecosystem |
| 14 | **REPL.io** | https://github.com/emyasnikov/replio | Python | Lightweight REPL + CLI + HTTP API | Zero-dependency, tool registry, permission gating | Actively maintained, minimal footprint |

## How to Choose

1. **Language & Ecosystem** - Pick a stack you are comfortable with (Python vs. TypeScript/JS vs. Go).
2. **Deployment Model** - Do you need a single process, a daemon, or an IDE plugin?
3. **Feature Set** - Do you need channel adapters, a desktop UI, or advanced agent orchestration?
4. **Community & Support** - Projects with active maintainers, frequent releases, and a strong community are safer bets for production use.
5. **LLM Provider Flexibility** - Some projects focus on a single provider (OpenAI), while others support a broad range of hosted and local models.

Feel free to explore the repositories, read the docs, and try the demos to find the best fit for your workflow.
