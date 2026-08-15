# Plugins

Plugins extend REPL.io with **tools**, **providers**, **slash commands**, and **services** without changing the core. The core stays stdlib-only; any third-party dependencies live inside the plugin and are imported lazily — they only matter when *you* install and use that plugin.

## Installation locations

| Root | Scope | Precedence |
|------|-------|------------|
| `replio.plugins.bundled` | **bundled** with replio (shipped in the package) | lowest |
| `~/.config/replio/plugins/` | global, all projects | middle |
| `.replio/plugins/` | local to a project | highest (wins on name collision) |

The three bundled first-party plugins ship with replio and are listed in the default `plugins` config so they are active out of the box: **`replio-core-websearch`** (web_search, fetch_page), **`replio-core-fs`** (read_file, list_dir, write_file, glob, grep), and **`replio-core-exec`** (run_command). They behave like any other plugin — disable them by removing their name from `plugins` (or `/plugins disable`), but they cannot be uninstalled or updated (they version with replio). A global or local plugin with the same name overrides the bundled one.

## Plugin layout

A plugin is a directory with a `manifest.json` and an entry module, or a bare `.py` file (name = filename, defaults apply):

```
~/.config/replio/plugins/web-scraper/
  manifest.json
  plugin.py          # entry module
  helpers.py         # sibling modules, importable by the entry
```

## Manifest

```json
{
  "name": "replio-web-scraper",
  "version": "0.3.1",
  "description": "Full-page scraping with links and structure",
  "replio_version": ">=0.12.0,<1.0",
  "python": ">=3.10",
  "entry": "plugin.py",
  "requires": ["beautifulsoup4", "lxml"],
  "provides": {"tools": ["scrape_page"], "providers": [], "commands": ["/scrape"]},
  "source": "https://github.com/example/replio-web-scraper"
}
```

| Key              | Default       | Description |
|------------------|---------------|-------------|
| `name`           | *(required)*  | Plugin name; also the install directory name |
| `version`        | `"0.0.0"`     | Plugin version |
| `description`    | `""`          | Shown in `/plugins` and `replio plugins list` |
| `replio_version` | `""`          | Semver range the plugin is compatible with (`>=0.12.0,<1.0`). Incompatible plugins are skipped at load |
| `python`         | `""`          | Minimum/maximum Python, same range syntax (`>=3.10`) |
| `entry`          | `"plugin.py"` | Module to load |
| `requires`       | `[]`          | Third-party packages; metadata for status + `--deps` install, never imported by the core |
| `provides`       | `{}`          | Declared tools/providers/commands for `/plugins` display |
| `source`         | `""`          | Origin recorded on install; used by `update` |

## Entry contract

The entry module may define any of four hooks (all optional):

```python
def register_tools(registry) -> None: ...        # @registry.register(...) — same as core tools
def register_providers(providers) -> None: ...   # providers["name"] = ProviderClass
def register_commands(commands) -> None: ...     # @commands.register(...) — same as core commands
def register_services(services) -> None: ...     # services["name"] = service object for core features
```

Plugin tools automatically inherit the tool permission policy, `/tool`, `/help`, query refinement, `noise_tools`, and session logging — the loop never special-cases plugin names.

### Services

`register_services` lets a plugin power a **core** feature that is not tool-calling. Today the only service is the web search-then-answer mode (`web_search: true`): the bundled `replio-core-websearch` registers `services['search']` with `search(query, num)`, `display(query, results)`, and `context(query, results)` methods. If no plugin registers the service, that mode reports that it is unavailable instead of erroring.

### Lazy dependencies

Keep third-party imports **inside** the tool function, not at module top level. A missing dependency then surfaces as a normal tool result with install guidance:

```python
def register_tools(registry):
    @registry.register(name='pdf2text', description='Extract text from a PDF',
                       parameters={'type': 'object', 'properties': {'path': {'type': 'string'}},
                                   'required': ['path']})
    def pdf2text(path):
        try:
            from pypdf import PdfReader
        except ImportError:
            return 'Error: pdf2text requires "pypdf" — pip install pypdf'
        ...
```

This is why the core stays zero-dependency: plugin packages are only imported in the process that runs your configured plugins, and only when their tools are actually called.

## Managing plugins

### Config activation

```json
{
  "plugins": ["replio-core-websearch", "replio-core-fs", "replio-core-exec"]
}
```

- `plugins` is the list of plugins to load. **Empty (`[]`) = all discovered plugins load.**
- The default config lists the bundled plugins so they are active by default; remove a name (or `/plugins disable`) to stop that plugin loading.
- `/plugins enable <name>` appends a name; `/plugins install` and `/plugins uninstall` add/remove the name automatically.
- Changes apply on the next start (plugins load once at engine init). `plugins.enabled` / `plugins.deny` from earlier versions are migrated automatically.

### REPL

```
/plugins                          # list plugins
/plugins <name>                   # detail: manifest, deps, status
/plugins enable <name>            # add to the plugins list, applies next start
/plugins disable <name>           # remove from the plugins list, applies next start
/plugins install <git-url|path> [--global] [--deps]
/plugins update <name>            # re-fetch from the recorded source
/plugins uninstall <name>
```

### CLI

The same operations are available headless (e.g. before a CI `replio run`):

```
replio plugins list
replio plugins install <git-url|path> --deps
replio plugins update <name>
replio plugins uninstall <name>
```

- `install` clones a git URL or copies a local directory into `.replio/plugins/` (or `~/.config/replio/plugins/` with `--global`), records `source`, and (with `--deps`) runs `pip install` on the declared `requires`.
- `update` runs `git pull` for remote sources or re-copies a local path.
- Bundled plugins report an error for `update`/`uninstall` — disable them instead.

## Status

`/plugins` (and `replio plugins list`) shows each plugin's name, version, **origin** (`bundled` / `global` / `local`), load status, and any unmet `requires`:

- `loaded` — active
- `disabled` — not in the `plugins` list (when it is non-empty)
- `incompatible` — `replio_version` or `python` range not satisfied (reason shown)
- `error` — invalid manifest, missing entry module, or the entry module raised while loading

## Security

Plugins are arbitrary Python code that run with your user's privileges — install only plugins you trust. A plugin's `register_providers` hook runs at load; its tools run on demand like any built-in tool.

## Future paths

- **Dependency isolation** — today plugin deps install into the same Python environment (lazy imports keep the core clean). Shared-plugin and per-plugin virtualenvs are planned for stronger separation.
- **PyPI source** — the same hooks will be discoverable through `importlib.metadata` entry points, so plugins can be distributed as regular packages.
- **Externalizing bundled plugins** — the bundled `replio-core-*` plugins are the migration path for optional features; web and machine tools now ship through them, and they can be forked or superseded by global/local plugins of the same name.
