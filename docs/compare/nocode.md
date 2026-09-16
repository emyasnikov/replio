# No-code

A **no-code** tool is turnkey: you install it or open it, configure agents and prompts through a UI, and use it without writing any code. You do not design a flow or write a plugin. You pick a model, give instructions, and go.

No-code tools win when the user is not a developer, when the goal is a chat or assistant experience rather than a running service, or when setup time matters more than control. They are a poor fit when you need to embed the runtime in your own system, script it, version the configuration, or run it on minimal hardware.

## Replio's position

Replio is not no-code. It is a terminal harness configured through text files and slash commands, so using it means working in a shell. What it does offer to a non-programmer is the `assistant` root: a single conversational entry point that greets the user, answers small tasks, and delegates bigger work, so the machinery stays out of sight. It is the opposite end from a turnkey UI, with the entire runtime auditable and local.

Most tools people call no-code agents are actually low-code visual builders, which are covered in [lowcode.md](lowcode.md). This page covers the truly turnkey products: a self-hosted chat UI, a visual platform, and the hosted assistants.

## Representatives

| Project | Language / stack | License | Configuration | Primary focus |
|---------|------------------|---------|---------------|---------------|
| AutoGPT platform | Python + TypeScript | MIT-style core plus a platform license | Visual blocks and marketplace | Hosted or self-hosted autonomous agents |
| Hosted assistants (ChatGPT, Claude, Gemini) | Closed | Commercial | Chat and settings only | General-purpose consumer assistants |
| Open WebUI | Python + TypeScript | Open source | Web UI and settings | Self-hosted chat UI over local and remote models |
| Replio | Python (stdlib only) | MIT | Text files and commands | Runnable agent harness with orchestration |

`Replio` is a harness listed for contrast.

## Profiles

### AutoGPT platform
An autonomous agent platform with a visual block builder, an agent marketplace, and both hosted and self-hosted options. It aims to make agent building accessible without code while still exposing blocks. Replio stays code-first and terminal-first.

### Hosted assistants
ChatGPT, Claude, and Gemini are the most-used no-code agents: a chat box, a model picker, and settings. They are closed, cloud-only, and cannot be embedded or self-hosted. Replio is the opposite: small, open, local-first, and scriptable.

### Open WebUI
A self-hosted chat interface over local models (Ollama) and OpenAI-compatible endpoints, with model management, retrieval, and extensions. It is the self-hosted answer to a hosted chat app. Replio shares the local-first stance but is a full agent harness rather than a chat UI.

## When to choose

| Scenario | Pick | Why |
|----------|------|-----|
| A non-developer wants a chat assistant with no setup code | Hosted assistants, Open WebUI | Turnkey UI, model picker, prompts |
| A self-hosted chat front-end over local models | Open WebUI | Local-first UI over Ollama and compatible APIs |
| An accessible agent builder without writing code | AutoGPT platform | Visual blocks and a marketplace |
| A small, auditable agent runtime you own and script | Replio | Stdlib core, text configuration, session logs |

## Sources and evidence

Replio facts come from this repository. Product facts come from each project's public documentation and repository, summarized at a level intended to stay stable. No performance or resource numbers are claimed here.

## References

- https://github.com/Significant-Gravitas/AutoGPT
- https://github.com/emyasnikov/replio
- https://github.com/open-webui/open-webui
- https://claude.ai
- https://chatgpt.com
- https://gemini.google.com
