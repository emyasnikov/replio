# Changelog

## 2026-07-27

### Added
- Project scaffold (pyproject.toml, .venv, directory structure)
- Config module: global + local JSON merge (`~/.config/replai/` + `.replai/`)
- HTTP SSE streaming via urllib for live token output
- Provider abstraction layer (OpenAI-compatible `/v1/chat/completions`)
- Ollama cloud provider (defaults to `https://api.ollama.com`)
- Session manager: create, list, load, delete, auto-save (JSON format)
- Command registry with decorator-based registration
- Built-in slash commands: `/help`, `/connect`, `/model`, `/provider`, `/session`, `/config`, `/exit`
- REPL loop with readline input history and tab completion
- Streaming token display with ANSI-colored prompt
- Documentation: README.md, AGENTS.md, TODO.md, CHANGELOG.md
