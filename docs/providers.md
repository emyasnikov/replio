# Providers

Providers are the model backends. Replio speaks OpenAI-compatible `/v1/chat/completions` to every provider. Providers only differ in base URL, default model, and occasionally auth or payload details. Each provider implements the event-generator `chat()` contract the agent loop consumes.

## Built-in providers

| Provider | Default base URL | Default model |
|----------|------------------|----------------|
| `ollama` | `https://api.ollama.com` | `llama3.2` |
| `openai` | `https://api.openai.com/v1` | `gpt-4o-mini` |
| `groq` | `https://api.groq.com/openai/v1` | `llama-3.3-70b-versatile` |
| `anthropic` | `https://api.anthropic.com/v1` | `claude-sonnet-4-20250514` |
| `openai-compatible` | *(none)* | *(none)* |

`openai-compatible` is the generic fallback for any other OpenAI-compatible endpoint - local models, gateways, or self-hosted servers.

## Configuration

`provider`, `base_url`, `model`, `api_key`, `temperature`, and `max_tokens` are configured in the global or local config (see [config.md](config.md)):

```json
{
  "provider": "openai",
  "base_url": "https://api.openai.com/v1",
  "model": "gpt-4o-mini",
  "api_key": "",
  "temperature": 0.7
}
```

The API key can also be supplied via `REPLIO_API_KEY` when running in a container.

## Auto-detection

When the configured provider name is unknown, or when `base_url` matches a known host, the provider is detected from the URL. `detect_provider()` matches `openai.com`, `groq.com`, `anthropic.com`, and `ollama.com` / `ollama.ai`, falling back to `openai-compatible` for anything else. `/connect` uses the same detection, so entering a base URL switches the provider automatically.

## Setting up

- `/connect` - interactive setup: provider, base URL, API key, model. Detects the provider from the entered base URL.
- `/model <name>` - show or switch the active model.
- `/provider <name>` - show or switch the active provider.
- `replio run --provider ... --model ... --base-url ...` - headless overrides.

## The `chat()` contract

`BaseProvider.chat(messages, stream=True, tools=None)` is a generator yielding events that the agent loop reacts to:

| Event | Payload | Meaning |
|-------|---------|---------|
| `thinking` | `content` | Reasoning tokens (from `reasoning_content` deltas) |
| `token` | `content` | Streamed content token(s) |
| `tool_calls` | `tool_calls` | Completed function-call objects requested by the model |
| `error` | `code`, `message` | Provider/network/HTTP error |
| `done` | `reason`, `usage` | Stream finished. `reason` is the finish reason, `usage` token counts when reported |

The loop runs one SSE stream per turn. When the model only produces content, that is a single round trip. `tool_calls` events append messages, execute the calls, and continue the loop until the model answers. The `<thinking>` marker split for reasoning embedded in content lives in the engine, so thinking stays separate from content.

`chat_nonstreaming(messages, tools=None)` is the non-streaming companion, used only for auxiliary decisions - query refinement, tool-result analysis, and compaction - never the main path.

## How the provider works

`OpenAICompatibleProvider` (`src/replio/providers/base.py`) builds an OpenAI-format payload (`model`, `messages`, `temperature`, optional `max_tokens`, optional `tools`, `stream`), POSTs it to `<base_url>/v1/chat/completions`, and streams the SSE response line by line. Streaming deltas are accumulated: `reasoning_content` becomes `thinking` events, `content` becomes `token` events, and fragmented `tool_calls` deltas are reassembled by index into complete function-call objects. HTTP and network errors are returned as `error` events.

`max_tokens` defaults to `0` = unset (omitted from the payload, so the provider's own default applies). A positive value caps output. Hitting it prints a warning and logs a session `errors` entry.

## Adding a provider

1. Create `src/replio/providers/<name>.py`.
2. Subclass `OpenAICompatibleProvider` and set `DEFAULT_BASE_URL` / `DEFAULT_MODEL`. Override `_headers()` / `_payload()` only for non-standard auth or request bodies.
3. Add the class to the `PROVIDERS` dict in `providers/__init__.py`.
4. Add a hostname match in `detect_provider()` so `/connect` auto-selects it.

Plugins can also register providers via their `register_providers(providers)` hook - `/connect` offers plugin providers automatically (see [plugins.md](plugins.md)).

## Streaming contract

The underlying SSE utility (`src/replio/utils/http.py`) reads the stream line by line with byte-buffered decoding, so multi-byte UTF-8 split across read chunks is handled correctly. Keep-alive and mid-stream errors surface as `error` events; a stream that ends without a completion event and with no streamed content is re-requested up to `1 + stream_retries` times (default 3 total attempts) with `stream_retry_delay` seconds between attempts before the "Stream ended before a completion event" error is reported. When tool calls have already run in the turn, the warning notes that the tool results are saved and the answer can be retried with a follow-up message.
