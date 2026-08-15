import importlib.util
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from ..config import Config
from .. import get_version


class PluginError(Exception):
    pass


@dataclass
class PluginInfo:
    name: str
    directory: Path
    global_: bool
    version: str = '0.0.0'
    description: str = ''
    entry: str = 'plugin.py'
    requires: list = field(default_factory=list)
    provides: dict = field(default_factory=dict)
    source: str = ''
    replio_version: str = ''
    python: str = ''
    status: str = 'loaded'
    error: str = ''


DEFAULT_PROVIDES = {'tools': [], 'providers': [], 'commands': []}


def version_matches(version: str, constraint: str) -> bool:
    if not constraint:
        return True
    for clause in constraint.split(','):
        clause = clause.strip()
        if not clause:
            continue
        op = None
        for candidate in ('>=', '<=', '==', '>', '<'):
            if clause.startswith(candidate):
                op = candidate
                value = clause[len(candidate):].strip()
                break
        if op is None:
            op = '=='
            value = clause
        cmp = _compare_versions(version, value)
        if op == '>=' and cmp < 0:
            return False
        if op == '<=' and cmp > 0:
            return False
        if op == '>' and cmp <= 0:
            return False
        if op == '<' and cmp >= 0:
            return False
        if op == '==' and cmp != 0:
            return False
    return True


def _version_key(version: str) -> tuple:
    parts = []
    for segment in str(version).split('.'):
        digits = ''
        for ch in segment:
            if ch.isdigit():
                digits += ch
            else:
                break
        parts.append(int(digits) if digits else 0)
    return tuple(parts[:3])


def _compare_versions(a: str, b: str) -> int:
    return (_version_key(a) > _version_key(b)) - (_version_key(a) < _version_key(b))


def _dep_installed(package: str) -> bool:
    try:
        return importlib.util.find_spec(package) is not None
    except (ImportError, ValueError, AttributeError):
        return False


class PluginManager:
    def __init__(self, config: Config):
        self.config = config
        self.global_dir = Path.home() / '.config' / 'replio' / 'plugins'
        self.local_dir = config.local_path.parent / 'plugins'
        self._modules: dict[str, object] = {}
        self._plugins: dict[str, PluginInfo] = {}
        self._provider_classes: dict[str, type] = {}

    def load(self):
        self._plugins = {}
        self._modules = {}
        self._provider_classes = {}
        for base in (self.global_dir, self.local_dir):
            if base.exists():
                self._discover(base)
        enabled = [str(n) for n in (self.config.get('plugins.enabled') or [])]
        denied = set(str(n) for n in (self.config.get('plugins.deny') or []))
        for name, info in list(self._plugins.items()):
            if name in denied or (enabled and name not in enabled):
                info.status = 'disabled'
                continue
            if info.status == 'error':
                continue
            if not self._compatible(info):
                info.status = 'incompatible'
                continue
            self._import(info)

    def _discover(self, base: Path):
        for entry in sorted(base.iterdir()):
            if entry.is_dir():
                manifest = entry / 'manifest.json'
                if not manifest.exists():
                    continue
                info = self._info_from_manifest(manifest, entry)
            elif entry.suffix == '.py':
                info = self._info_from_file(entry)
            else:
                continue
            self._plugins[info.name] = info

    def _info_from_manifest(self, manifest_path: Path, entry_dir: Path) -> PluginInfo:
        try:
            with open(manifest_path) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            return self._build_info({'error': f'invalid manifest: {e}'},
                                    entry_dir, entry_dir.name)
        if not isinstance(data, dict):
            return self._build_info({'error': 'invalid manifest: not an object'},
                                    entry_dir, entry_dir.name)
        return self._build_info(data, entry_dir, data.get('name') or entry_dir.name)

    def _info_from_file(self, path: Path) -> PluginInfo:
        side = path.with_suffix('.json')
        data = {}
        if side.exists():
            try:
                with open(side) as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError):
                data = {}
            if not isinstance(data, dict):
                data = {}
        data['entry'] = path.name
        return self._build_info(data, path.parent, data.get('name') or path.stem)

    def _build_info(self, data: dict, directory: Path, name: str) -> PluginInfo:
        error = data.pop('error', '') if isinstance(data, dict) else ''
        info = PluginInfo(
            name=name,
            directory=directory,
            global_=directory.is_relative_to(self.global_dir),
            version=str(data.get('version') or '0.0.0'),
            description=str(data.get('description') or ''),
            entry=str(data.get('entry') or 'plugin.py'),
            requires=list(data.get('requires') or []),
            provides=dict(data.get('provides') or {}),
            source=str(data.get('source') or ''),
            replio_version=str(data.get('replio_version') or ''),
            python=str(data.get('python') or ''),
        )
        if error:
            info.status = 'error'
            info.error = error
        return info

    def _compatible(self, info: PluginInfo) -> bool:
        current = get_version()
        if info.replio_version and current != 'unknown':
            if not version_matches(current, info.replio_version):
                info.error = f'replio {current} does not satisfy {info.replio_version}'
                return False
        if info.python:
            py = f'{sys.version_info.major}.{sys.version_info.minor}'
            if not version_matches(py, info.python):
                info.error = f'python {py} does not satisfy {info.python}'
                return False
        return True

    def _import(self, info: PluginInfo):
        entry_path = info.directory / info.entry
        if not entry_path.exists():
            info.status = 'error'
            info.error = f'entry module not found: {info.entry}'
            return
        mod_name = f'_replio_plugin_{info.name}'
        try:
            spec = importlib.util.spec_from_file_location(mod_name, str(entry_path))
            if spec is None or spec.loader is None:
                raise ImportError(f'cannot load {entry_path}')
            module = importlib.util.module_from_spec(spec)
            module.__package__ = mod_name
            module.__path__ = [str(info.directory)]
            sys.modules[mod_name] = module
            added = False
            if str(info.directory) not in sys.path:
                sys.path.insert(0, str(info.directory))
                added = True
            try:
                spec.loader.exec_module(module)
            finally:
                if added:
                    sys.path.remove(str(info.directory))
            info.status = 'loaded'
            self._modules[info.name] = module
            hook = getattr(module, 'register_providers', None)
            if hook:
                providers: dict[str, type] = {}
                hook(providers)
                self._provider_classes.update(providers)
        except Exception as e:
            info.status = 'error'
            info.error = str(e)

    def register_tools(self, registry):
        for name, module in self._modules.items():
            if self._plugins[name].status != 'loaded':
                continue
            hook = getattr(module, 'register_tools', None)
            if not hook:
                continue
            try:
                hook(registry)
            except Exception as e:
                info = self._plugins[name]
                info.status = 'error'
                info.error = f'register_tools failed: {e}'

    def register_commands(self, registry):
        for name, module in self._modules.items():
            if self._plugins[name].status != 'loaded':
                continue
            hook = getattr(module, 'register_commands', None)
            if not hook:
                continue
            try:
                hook(registry)
            except Exception as e:
                info = self._plugins[name]
                info.status = 'error'
                info.error = f'register_commands failed: {e}'

    def provider_classes(self) -> dict[str, type]:
        return dict(self._provider_classes)

    def status(self) -> list[PluginInfo]:
        return list(self._plugins.values())

    def get(self, name: str) -> PluginInfo | None:
        return self._plugins.get(name)

    def dep_status(self, info: PluginInfo) -> list[tuple[str, bool]]:
        return [(pkg, _dep_installed(pkg)) for pkg in info.requires]

    def install(self, source: str, global_: bool = False,
                deps: bool = False) -> PluginInfo:
        dest_root = self.global_dir if global_ else self.local_dir
        name = self._fetch(source, dest_root)
        self.load()
        info = self._plugins.get(name)
        if info is None:
            raise PluginError(f'installed plugin "{name}" could not be loaded')
        if deps and info.requires:
            for pkg in info.requires:
                self._pip_install(pkg)
        return info

    def update(self, name: str) -> PluginInfo:
        info = self._plugins.get(name)
        if info is None:
            raise PluginError(f'plugin not installed: {name}')
        if not info.source:
            raise PluginError(f'plugin {name} has no recorded source to update from')
        if self._is_url(info.source):
            proc = subprocess.run(['git', 'pull'], cwd=str(info.directory),
                                  capture_output=True, text=True)
            if proc.returncode != 0:
                raise PluginError(
                    f'git pull failed: {proc.stderr.strip() or proc.stdout.strip()}')
        else:
            fetched = Path(info.source).expanduser().resolve()
            if not fetched.is_dir():
                raise PluginError(f'update source not found: {info.source}')
            shutil.rmtree(info.directory)
            shutil.copytree(fetched, info.directory)
        self._write_source(info.directory, name, info.source)
        self.load()
        updated = self._plugins.get(name)
        if updated is None:
            raise PluginError(f'plugin {name} could not be reloaded after update')
        return updated

    def uninstall(self, name: str) -> None:
        info = self._plugins.get(name)
        if info is None:
            raise PluginError(f'plugin not installed: {name}')
        if info.directory.exists():
            shutil.rmtree(info.directory)
        self.load()

    def install_deps(self, info: PluginInfo) -> None:
        for pkg in info.requires:
            self._pip_install(pkg)

    def _pip_install(self, package: str) -> None:
        proc = subprocess.run([sys.executable, '-m', 'pip', 'install', package],
                              capture_output=True, text=True)
        if proc.returncode != 0:
            raise PluginError(
                f'pip install {package} failed: {proc.stderr.strip()[-400:]}')

    def _fetch(self, source: str, dest_root: Path) -> str:
        dest_root.mkdir(parents=True, exist_ok=True)
        original = source.strip()
        if self._is_url(original):
            tmp = dest_root / '.install_tmp'
            if tmp.exists():
                shutil.rmtree(tmp)
            proc = subprocess.run(['git', 'clone', original, str(tmp)],
                                  capture_output=True, text=True)
            if proc.returncode != 0:
                raise PluginError(
                    f'git clone failed: {proc.stderr.strip() or proc.stdout.strip()}')
            fetched = tmp
            cleanup = True
        else:
            fetched = Path(original).expanduser().resolve()
            if not fetched.is_dir():
                raise PluginError(f'plugin source not found: {original}')
            cleanup = False
        try:
            name = self._plugin_name(fetched)
            dest = dest_root / name
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(fetched, dest)
            self._write_source(dest, name, original)
            return name
        finally:
            if cleanup and tmp.exists():
                shutil.rmtree(tmp)

    def _plugin_name(self, fetched: Path) -> str:
        manifest = fetched / 'manifest.json'
        name = ''
        if manifest.exists():
            try:
                with open(manifest) as f:
                    name = str(json.load(f).get('name') or '')
            except (json.JSONDecodeError, OSError):
                name = ''
        name = name or fetched.name
        cleaned = ''.join(c if c.isalnum() or c in '-_.' else '_'
                          for c in name).strip('.')
        if not cleaned:
            raise PluginError(f'could not determine plugin name from {fetched}')
        return cleaned

    def _write_source(self, directory: Path, name: str, source: str) -> None:
        manifest_path = directory / 'manifest.json'
        data = {'name': name}
        if manifest_path.exists():
            try:
                with open(manifest_path) as f:
                    data.update(json.load(f))
            except (json.JSONDecodeError, OSError):
                pass
        data['source'] = source
        with open(manifest_path, 'w') as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def _is_url(source: str) -> bool:
        return source.startswith(('http://', 'https://', 'git://',
                                  'git@', 'ssh://'))
