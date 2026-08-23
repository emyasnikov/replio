# Troubleshooting

## Repeated "Assistant output truncated" / "empty response"

Two warnings that often appear together in agentic sessions:

- `[warning] Assistant output truncated (max_tokens reached); use /config max_tokens N`
- `[warning] Assistant returned an empty response`

### What each one means

1. **Truncation** fires when a turn ends with `finish_reason = "length"` - the output-token budget was spent and the provider stopped generating. The budget is `max_tokens` when set (`0` omits it and the provider default applies). The warning distinguishes a configured cap from the provider's own default.

2. **Empty response** is a separate path: a stream completed normally (`[DONE]`) but produced no content. Today it retries like any empty stream (`stream_retries`) before being flagged, and reasoning-only turns (thinking present, content empty) are no longer treated as errors.

### A worked case: `nemotron-3-nano:30b-cloud` on ollama.com

A real session showed the pair repeatedly. Root causes, in order of impact:

- **A low explicit `max_tokens`.** The project config pinned `max_tokens: 2048` (the repo default is 8192). The model burned the whole output budget inside its chain-of-thought and cut off before any answer - so `finish_reason = length` with empty content, then a follow-up "Continue" came back empty. Raise it or set `0`:

  ```
  replio config set max_tokens 0 --global
  ```

- **Thinking was generated but never displayed.** The endpoint streams the CoT under `delta.reasoning` (not `delta.reasoning_content` which older OpenAI-compatible endpoints use). The provider now reads both keys, so reasoning shows in the REPL (`show_thinking`) and is persisted again. Before that fix the reasoning tokens counted against the cap but were silently invisible.

- **Recovery.** `auto_continue` (default `true`) now re-requests the turn with a "continue exactly where you stopped" instruction when a partial answer is truncated, stitching the parts into one message (capped by `auto_continue_max`, default 2). Partial content AND thinking are persisted even when a turn ends truncated or in an error, so nothing is silently lost.

### Config layering and secrets

Config is read per key with project-local values winning: built-in defaults, then the global file (`~/.config/replio/config.json`), then the project file (`.replio/config.json`). None of the files is distributed - every process merges them in memory.

Writes are scoped:

- `api_key` is always stored in the **global** file (`replio config set api_key ...`), never in the project file. The global file is written with `0600` permissions when it holds a key.
- Everything else writes to the **project-local** file by default. `replio config set KEY VALUE --global` targets the global file.
- The project-local file holds only what was selected locally. A save never re-writes the merged config, so a global secret can not be copied down by a stray `/config` write.

If a key was already stored in a project config, loading it moves it to the global file and drops it locally, printing a notice.

### General checks

- `replio config get max_tokens --show-origin` - where the current cap comes from.
- `replio config get provider model base_url --show-origin` - which scope holds your connection.
- For long answering that still truncates, raise `max_tokens` or increase `auto_continue_max`.