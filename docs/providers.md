# Providers

Providers are the model backends. Replio speaks OpenAI-compatible `/v1/chat/completions` to every provider. Providers only differ in base URL, default model, and occasionally auth or payload details. Each provider implements the event-generator `chat()` contract the agent loop consumes.

## Built-in providers

| Provider | Default base URL | Default model |
|----------|------------------|----------------|
| `ollama` | `https://api.ollama.com` | `llama3.2` |
| `openai` | `https://api.openai.com/v1` | `gpt-4o-mini` |
| `groq` | `https://api.groq.com/openai/v1` | `llama-3.3-70b-versatile` |
| `anthropic` | `https://api.anthropic.com/v1` | `claude-sonnet-4-20250514` |
| `opencode` | `https://opencode.ai/zen/v1` | `kimi-k3` |
| `opencode-go` | `https://opencode.ai/zen/go/v1` | `deepseek-v4-flash` |
| `openai-compatible` | *(none)* | *(none)* |

`openai-compatible` is the generic fallback for any other OpenAI-compatible endpoint - local models, gateways, or self-hosted servers.

`opencode` (Zen) and `opencode-go` (Go) are the two hosted catalogs at `opencode.ai`. Both use the same OpenCode API key (`OPENCODE_API_KEY`, resolved from the model registry like any other provider) but are separate paid subscriptions. Zen is the curated multi-model gateway. Go is the low-cost subscription for open coding models. Model refs accept the `opencode/<model-id>` and `opencode-go/<model-id>` conventions as well as bare model ids - the prefix is stripped before the request. A successful model listing is an inventory, not an entitlement check: inference still requires the matching subscription. Fetch the current lineup from `https://opencode.ai/zen/v1/models` and `https://opencode.ai/zen/go/v1/models`.

## Configuration

`provider`, `base_url`, `model`, `temperature`, and `max_tokens` are configured in the global or local config (see [config.md](config.md)). The API key is **not** a config value - it lives in the global provider registry (`~/.config/replio/providers.json`, one key per provider) and is managed through `/connect`:

```json
{
  "provider": "openai",
  "base_url": "https://api.openai.com/v1",
  "model": "gpt-4o-mini",
  "temperature": 0.7
}
```

The engine resolves the API key for the active provider from the provider registry (a `(key)` entry from `/connect`), falling back to `""` - no environment variable is consulted. A custom `base_url` stored there is used when the config leaves it empty. The approved-model history (`~/.config/replio/models.json`) records every model used for `/model list`.

## Model refs and approval

A **model ref** `provider/model` (e.g. `opencode-go/deepseek-v4-flash`, `ollama/gpt-oss:20b-cloud`) unfolds to the provider, its default base URL, and the bare model. It is accepted wherever a model is set - `/model <ref>`, `--model <ref>`, a config `model`, and an agent type's `model` field - so a type or team can pin provider and model together. Only a known provider (core or plugin) with a default base URL unfolds; anything else is treated as a bare model id.

Using an unfolded model is **gated on approval**: the model must appear in `models.json`, otherwise the engine prompts to approve it. The surfaces:

- **Interactive** - the REPL asks on load for an unapproved configured ref, `/model <ref>` asks before switching, and `/team run` pre-checks the stages' type models and asks once for any unapproved ones.
- **Headless** - an explicit `--model` auto-approves (records into `models.json`). A model referenced by an agent type or team is denied unless `--approve-model` is passed (`replio run --approve-model`, `replio jobs add --approve-model`, `replio fleet config --approve-model`). A denied run stops with a clear "model not approved" error.

A ref naming a provider with no stored key still switches to it but prints `run /connect <provider>` (the request then surfaces the auth error until you connect).

## Auto-detection

When the configured provider name is unknown, or when `base_url` matches a known host, the provider is detected from the URL. `detect_provider()` matches `openai.com`, `groq.com`, `anthropic.com`, `ollama.com` / `ollama.ai`, and `opencode.ai` (path `/zen/go` selects `opencode-go`, otherwise `opencode`), falling back to `openai-compatible` for anything else. `/connect` uses the same detection, so passing a base URL switches the provider automatically. A URL that equals a plugin provider's default base URL selects that plugin provider (see [plugins.md](plugins.md)); a registry-named custom provider (one created by `/connect <url>`) resolves as an OpenAI-compatible connection.

## Setting up

`/connect` connects a provider and stores its API key (and any custom base URL) in the global `providers.json` registry - it never touches the model, which is picked separately with `/model`:

- `/connect` - interactive picker: a numbered list of known providers (core + plugins) with a `(key)` marker when a key is stored. The prompt accepts a number, a provider name, or a URL.
- `/connect <name>` - connect a known provider by name (e.g. `ollama`, `openai`, `groq`, `anthropic`, `opencode`, `opencode-go`). The provider's default base URL is preset; you only enter the API key. A stored key is shown as the default - press Enter to keep it or type to replace it (re-enter a missing or stale key).
- `/connect <url>` - connect by URL. A known host (or a plugin provider's default URL) selects that provider with the URL as its base URL; anything else creates a named custom provider, with the name derived from the host (e.g. `https://llm.acme.example/v1` -> `acme-example`).
- `/connect <url> <name>` - custom provider with an explicit name instead of the derived one.

All forms **test the connection** (a `GET <base_url>/v1/models` probe) before saving: broken values are rejected unless you confirm `Save anyway?`. A successful connect prints `Connected to <provider> (<base_url>)`, records the entry in `providers.json`, writes `provider`/`base_url` into the config, and points you at `/model list --online <provider>` to pick a model.

Related surfaces: `/model <name>` shows or switches the active model (a `provider/model` ref switches provider and model together, approving the model), `/models` (alias `/model-list`) lists the models the connected provider advertises, `/provider <name>` shows or switches the active provider, and `replio run --provider ... --model ... --base-url ...` provides headless overrides.

Connection probing is gated by the `connect_check` config (default `true`). Set it to `false` to skip the probes (e.g. offline or flaky networks). `OpenAICompatibleProvider.check_connection()` returns `(ok, message)` by reusing `_fetch_models()` - the shared `GET /v1/models` helper that `list_models()` also uses.

## The `chat()` contract

`BaseProvider.chat(messages, stream=True, tools=None)` is a generator yielding events that the agent loop reacts to:

| Event | Payload | Meaning |
|-------|---------|---------|
| `thinking` | `content` | Reasoning tokens (from `reasoning_content` or `reasoning` deltas - some OpenAI-compatible endpoints such as ollama.com use `reasoning`) |
| `token` | `content` | Streamed content token(s) |
| `tool_calls` | `tool_calls` | Completed function-call objects requested by the model |
| `error` | `code`, `message` | Provider/network/HTTP error |
| `done` | `reason`, `usage` | Stream finished. `reason` is the finish reason, `usage` token counts when reported |

The loop runs one SSE stream per turn. When the model only produces content, that is a single round trip. `tool_calls` events append messages, execute the calls, and continue the loop until the model answers. The `<thinking>` marker split for reasoning embedded in content lives in the engine, so thinking stays separate from content.

`chat_nonstreaming(messages, tools=None)` is the non-streaming companion, used only for auxiliary decisions - query refinement, tool-result analysis, and compaction - never the main path.

## How the provider works

`OpenAICompatibleProvider` (`src/replio/providers/base.py`) builds an OpenAI-format payload (`model`, `messages`, `temperature`, optional `max_tokens`, optional `tools`, `stream`), POSTs it to `<base_url>/v1/chat/completions`, and streams the SSE response line by line. Streaming deltas are accumulated: `reasoning_content` (or `reasoning` on endpoints such as ollama.com) becomes `thinking` events, `content` becomes `token` events, and fragmented `tool_calls` deltas are reassembled by index into complete function-call objects. HTTP and network errors are returned as `error` events.

`max_tokens` defaults to `8192` (sent to the provider, overriding low provider-side defaults like Ollama's 2048 cap). Set it to `0` to omit it from the payload, in which case the provider's own default applies. Hitting the limit prints a warning and logs a session `errors` entry - the warning text distinguishes a configured cap from the provider's default.

## Requesting reasoning

The `reasoning` config (default `"auto"`) tells the model reasoning is desired and controls its token budget. It is orthogonal to `show_thinking` (which only controls display). Values: `false`/`"off"` = do not request, `true`/`"on"`/`"auto"` = request with the provider default, `"low"`/`"medium"`/`"high"` = explicit budget hint. The provider maps it to its own parameter:

| Provider | off / false | low / medium / high | on / auto |
|----------|-------------|----------------------|-----------|
| `openai` | no `reasoning_effort` | `reasoning_effort = "low"\|"medium"\|"high"` | `reasoning_effort = "medium"` |
| `anthropic` | `thinking: {type: "disabled"}` | `thinking: {type: "enabled", budget_tokens: 1024\|2048\|4096}` | `thinking: {type: "enabled", budget_tokens: 2048}` |
| `ollama` (Qwen) | `enable_thinking: false` | `enable_thinking: true` (`chat_template_kwargs.thinking: true`) | `enable_thinking: true` |
| other / `openai-compatible` / `opencode` / `opencode-go` | nothing | `reasoning_effort` pass-through | nothing (provider default) |

## Adding a provider

1. Create `src/replio/providers/<name>.py`.
2. Subclass `OpenAICompatibleProvider` and set `DEFAULT_BASE_URL` / `DEFAULT_MODEL`. Override `_headers()` / `_payload()` only for non-standard auth or request bodies.
3. Add the class to the `PROVIDERS` dict in `providers/__init__.py`.
4. Add a hostname match in `detect_provider()` so `/connect` auto-selects it.

Plugins can also register providers via their `register_providers(providers)` hook - `/connect` offers plugin providers automatically (see [plugins.md](plugins.md)).

## Streaming contract

The underlying SSE utility (`src/replio/utils/http.py`) reads the stream line by line with byte-buffered decoding, so multi-byte UTF-8 split across read chunks is handled correctly. Keep-alive and mid-stream errors surface as `error` events. A stream that ends without a completion event and with no streamed content is re-requested up to `1 + stream_retries` times (default 3 total attempts) with `stream_retry_delay` seconds between attempts before the "Stream ended before a completion event" error is reported. When tool calls have already run in the turn, the warning notes that the tool results are saved and the answer can be retried with a follow-up message.
