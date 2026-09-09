# Replio Documentation

Detailed reference for Replio. For the overview, features, and quick start, see the [README](../README.md).

- [API endpoints](api.md) - HTTP JSON API for `replio serve`
- [Architecture](architecture.md) - agent core: the loop, engine, UI sinks, front-ends, extension points
- [Commands & CLI](commands.md) - slash commands and headless CLI flags
- [Configuration](config.md) - config schema and keys
- [Deployment](deploy.md) - Docker deployment (image + Compose fleet)
- [Eval harness](eval.md) - tool-use evaluation (`replio eval`), task fixtures, metrics
- [Agent fleets](fleet.md) - single-purpose agent fleets, one scoped process per agent, deployment
- [Jobs](jobs.md) - scheduled and durable jobs (`replio jobs`), cron scheduling, approvals
- [Model Context Protocol](mcp.md) - MCP client and server
- [Plugins](plugins.md) - bundled, layout, manifest, management
- [Providers](providers.md) - providers, auto-detection, the chat event contract, adding a provider
- [Security](security.md) - permission model, threat model, data posture, prompt injection
- [Sessions](session.md) - session log format, message schema, compaction, persistence
- [Skills](skills.md) - skill registry, storage, type injection
- [Agent swarms](swarm.md) - swarm orchestration, delegation, types, auditor and team patterns
- [Testing](testing.md) - running the mock test suite, per-file coverage map
- [Tools](tools.md) - tool registry, bundled tools, tool policy, registration metadata
- [Agent types](types.md) - type catalog, storage, delegation and permission rule
- [Usage](usage/) - step-by-step setup variations
- [Use cases](use-cases/) - fit and adoption guides for enterprise, personal, etc.
- [Versus](vs/) - Replio vs. OpenClaw, Hermes and broader landscape
- [Writing tools for agents](writing-tools.md) - how to design, name, and describe tools for the agent loop
