# Plugins

Plugins extend Replio with **tools**, **providers**, **slash commands**, and **services** without changing the core. The core stays stdlib-only. Any third-party dependencies live inside the plugin and are imported lazily, so they only matter when you install and use that plugin.

## Installation locations

| Root | Scope | Precedence |
|------|-------|------------|
| `replio.plugins.bundled` | **bundled** with replio (shipped in the package) | lowest |
| `~/.config/replio/plugins/` | global, all projects | middle |
| `.replio/plugins/` | local to a project | highest (wins on name collision) |

First-party plugins ship with replio and are listed in the default `plugins` config, so they are active out of the box. `replio-core-web` provides `web_search` and `web_fetch`. `replio-core-fs` provides `file_read`, `list_dir`, `file_write`, `glob`, and `grep`. `replio-core-exec` provides `run_command`. `replio-core-mcp` provides the MCP client (`mcp_connect`/`mcp_list`/`mcp_disconnect`) and server (`replio mcp` and `POST /mcp`) - see [mcp.md](mcp.md). `replio-core-eval` provides the eval fixture catalog for `replio eval` - see [eval.md](eval.md). They behave like any other plugin. Remove a name from `plugins` (or use `/plugins disable`) to stop it loading, but they cannot be uninstalled or updated, since they version with replio. A global or local plugin with the same name overrides the bundled one.

## Plugin layout

A plugin is a directory with a `manifest.json`, an entry module, and an optional unit-test suite. Source modules live under `src/` and tests under `tests/` (a bare `.py` file at the root is also accepted - name = filename, defaults apply):

```
~/.config/replio/plugins/web-scraper/
  manifest.json
  src/
    plugin.py          # entry module (manifest "entry" points here)
    helpers.py         # sibling modules, importable by the entry
  tests/
    test_plugins.py    # optional - run by `replio plugins test` and the core suite
```

The entry module may sit anywhere under the plugin directory - `manifest.json` `"entry"` is a path relative to the plugin root (default `plugin.py`). Sibling imports resolve from the entry module's own directory, so a `src/` layout works the same as a flat one.

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
| `name`           | *(required)*  | Plugin name, also the install directory name |
| `version`        | `"0.0.0"`     | Plugin version |
| `description`    | `""`          | Shown in `/plugins` and `replio plugins list` |
| `replio_version` | `""`          | Semver range the plugin is compatible with (`>=0.12.0,<1.0`). Incompatible plugins are skipped at load |
| `python`         | `""`          | Minimum/maximum Python, same range syntax (`>=3.10`) |
| `entry`          | `"plugin.py"` | Module to load, relative to the plugin directory (may point into `src/`) |
| `requires`       | `[]`          | Third-party packages, metadata for status and `--deps` install, never imported by the core |
| `provides`       | `{}`          | Declared tools/providers/commands for `/plugins` display |
| `source`         | `""`          | Origin recorded on install, used by `update` |

## Entry contract

The entry module may define any of eight hooks (all optional):

```python
def register_tools(registry) -> None: ...        # @registry.register(...) - same as core tools
def register_providers(providers) -> None: ...   # providers["name"] = ProviderClass
def register_commands(commands) -> None: ...     # @commands.register(...) - same as core commands
def register_services(services) -> None: ...     # services["name"] = service object for core features
def register_types(registry) -> None: ...     # registry.add_plugin({...}) - plugin-owned types
def register_teams(teams) -> None: ...           # register into the TeamRegistry (see swarm.md)
def register_skills(skills) -> None: ...         # skills.add_plugin({...}) - see skills.md
def register_fixtures(fixtures) -> None: ...     # fixtures["id"] = fixture data - see eval.md
```

Plugin tools automatically inherit the tool permission policy, `/tool`, `/help`, query refinement, `noise_tools`, and session logging. The loop never special-cases plugin names.

A tool handler may declare a `_config` keyword argument to receive the engine's `Config` (e.g. to read a config key like `tool_max_result_chars`). The registry passes it only when the handler's signature accepts it, and it is never exposed to the model. See [tools.md](tools.md).

### Providers

`register_providers` contributes to the same provider set as the core `PROVIDERS` dict: the plugin provider appears in the `/connect` picker, and passing its `DEFAULT_BASE_URL` as a `/connect <url>` argument selects it automatically (see [providers.md](providers.md)). A plugin provider's `DEFAULT_BASE_URL` also makes it a model-ref target (`<name>/<model>`).

### Services

`register_services` lets a plugin power a core feature that is not tool-calling. Today the only service is the web search-then-answer mode (`web_search: true`). The bundled `replio-core-web` registers `services['search']` with `search(query, num)`, `display(query, results)`, and `context(query, results)` methods. If no plugin registers the service, that mode reports that it is unavailable instead of erroring.

### Agent types, teams, and skills

`register_types(registry)` contributes types to the `TypeRegistry` via `registry.add_plugin(entry)` (same entry shape as `types.json`). Plugin types form an in-memory layer between bundled and global, so precedence is `bundled < plugin < global < local`, and a `types.json` entry can always override or replace a plugin-provided type. `register_teams(teams)` and `register_skills(skills)` register into the team and skills registries the same way (`teams.add_plugin(...)` / `skills.add_plugin(...)`, entry shapes in [teams.md](teams.md) and [skills.md](skills.md)). The `/type` list marks plugin types `(plugin)`, and after `/plugins install`/`update`/`uninstall` the running REPL re-applies all three hooks immediately. Tools and commands still activate on the next start.

### Eval fixtures

`register_fixtures(fixtures)` contributes task fixtures to the tool-use evaluation harness. The hook receives a dict of fixture `id` to fixture data (same shape as the JSON fixtures under `.replio/eval/`, see [eval.md](eval.md)). Local and global fixture files override plugin fixtures by `id`. The bundled `replio-core-eval` plugin ships the default catalog this way.

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
            return 'Error: pdf2text requires "pypdf" - pip install pypdf'
        ...
```

This is why the core stays zero-dependency. Plugin packages are only imported in the process that runs your configured plugins, and only when their tools are actually called.

## Managing plugins

### Config activation

```json
{
  "plugins": ["replio-core-web", "replio-core-fs", "replio-core-exec"]
}
```

- `plugins` is the list of plugins to load. **Empty (`[]`) = all discovered plugins load.**
- The default config lists the bundled plugins so they are active by default. Remove a name (or `/plugins disable`) to stop that plugin loading.
- `/plugins enable <name>` appends a name. `/plugins install` and `/plugins uninstall` add or remove the name automatically.
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

The same operations are available headless (for example before a CI `replio run`):

```
replio plugins list
replio plugins install <git-url|path> --deps
replio plugins update <name>
replio plugins uninstall <name>
replio plugins test [name]
```

- `install` clones a git URL or copies a local directory into `.replio/plugins/` (or `~/.config/replio/plugins/` with `--global`), records `source`, and with `--deps` runs `pip install` on the declared `requires`.
- `update` runs `git pull` for remote sources or re-copies a local path.
- `test` runs a plugin's `tests/` unit suite (`--verbose` for per-test output). Without a name it runs every plugin that has one. The core test suite also runs these through `tests/test_plugin_suites.py`.
- Bundled plugins report an error for `update` and `uninstall`. Disable them instead.

## Status

`/plugins` (and `replio plugins list`) shows each plugin's name, version, **origin** (`bundled` / `global` / `local`), load status, and any unmet `requires`:

- `loaded` - active
- `disabled` - not in the `plugins` list (when it is non-empty)
- `incompatible` - `replio_version` or `python` range not satisfied (reason shown)
- `error` - invalid manifest, missing entry module, or the entry module raised while loading

## Security

Plugins are arbitrary Python code that run with your user's privileges. Install only plugins you trust. A plugin's `register_providers` hook runs at load. Its tools run on demand like any built-in tool.

## Future paths

- **Dependency isolation**: today plugin deps install into the same Python environment (lazy imports keep the core clean). Shared-plugin and per-plugin virtualenvs are planned for stronger separation.
- **PyPI source**: the same hooks will be discoverable through `importlib.metadata` entry points, so plugins can be distributed as regular packages.
- **Externalizing bundled plugins**: the bundled `replio-core-*` plugins are the migration path for optional features. Web and machine tools now ship through them, and they can be forked or superseded by global/local plugins of the same name.
