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

The API key is read from the `api_key` config value (global or local `.replio/config.json`), no environment variable is consulted.

## Auto-detection

When the configured provider name is unknown, or when `base_url` matches a known host, the provider is detected from the URL. `detect_provider()` matches `openai.com`, `groq.com`, `anthropic.com`, and `ollama.com` / `ollama.ai`, falling back to `openai-compatible` for anything else. `/connect` uses the same detection, so entering a base URL switches the provider automatically.

## Setting up

- `/connect` - interactive setup: provider, base URL, API key, model. Detects the provider from the entered base URL, then **tests the connection** (a `GET <base_url>/v1/models` probe) before saving: broken values are rejected unless you confirm `Save anyway?`.
- `/model <name>` - show or switch the active model.
- `/provider <name>` - show or switch the active provider. After switching, the connection is probed and a warning is shown on failure (`/connect` is the fix).
- `replio run --provider ... --model ... --base-url ...` - headless overrides.

Connection probing is gated by the `connect_check` config (default `true`); set it to `false` to skip the probes (e.g. offline/flaky networks). `OpenAICompatibleProvider.check_connection()` returns `(ok, message)` by reusing `_fetch_models()` - the shared `GET /v1/models` helper that `list_models()` also uses.

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

`max_tokens` defaults to `8192` (sent to the provider, overriding low provider-side defaults like Ollama's 2048 cap). Set it to `0` to omit it from the payload, in which case the provider's own default applies. Hitting the limit prints a warning and logs a session `errors` entry - the warning text distinguishes a configured cap from the provider's default.

## Requesting reasoning

The `reasoning` config (default `"auto"`) tells the model reasoning is desired and controls its token budget. It is orthogonal to `show_thinking` (which only controls display). Values: `false`/`"off"` = do not request, `true`/`"on"`/`"auto"` = request with the provider default, `"low"`/`"medium"`/`"high"` = explicit budget hint. The provider maps it to its own parameter:

| Provider | off / false | low / medium / high | on / auto |
|----------|-------------|----------------------|-----------|
| `openai` | no `reasoning_effort` | `reasoning_effort = "low"\|"medium"\|"high"` | `reasoning_effort = "medium"` |
| `anthropic` | `thinking: {type: "disabled"}` | `thinking: {type: "enabled", budget_tokens: 1024\|2048\|4096}` | `thinking: {type: "enabled", budget_tokens: 2048}` |
| `ollama` (Qwen) | `enable_thinking: false` | `enable_thinking: true` (`chat_template_kwargs.thinking: true`) | `enable_thinking: true` |
| other / `openai-compatible` | nothing | `reasoning_effort` pass-through | nothing (provider default) |

## Adding a provider

1. Create `src/replio/providers/<name>.py`.
2. Subclass `OpenAICompatibleProvider` and set `DEFAULT_BASE_URL` / `DEFAULT_MODEL`. Override `_headers()` / `_payload()` only for non-standard auth or request bodies.
3. Add the class to the `PROVIDERS` dict in `providers/__init__.py`.
4. Add a hostname match in `detect_provider()` so `/connect` auto-selects it.

Plugins can also register providers via their `register_providers(providers)` hook - `/connect` offers plugin providers automatically (see [plugins.md](plugins.md)).

## Streaming contract

The underlying SSE utility (`src/replio/utils/http.py`) reads the stream line by line with byte-buffered decoding, so multi-byte UTF-8 split across read chunks is handled correctly. Keep-alive and mid-stream errors surface as `error` events. A stream that ends without a completion event and with no streamed content is re-requested up to `1 + stream_retries` times (default 3 total attempts) with `stream_retry_delay` seconds between attempts before the "Stream ended before a completion event" error is reported. When tool calls have already run in the turn, the warning notes that the tool results are saved and the answer can be retried with a follow-up message.
