from typing import NamedTuple

from .config import Config


class ModeSpec(NamedTuple):
    name: str
    instruction: str
    permissions: dict
    deny: list
    allow: list


def _normalize_spec(name: str, spec: dict) -> ModeSpec:
    spec = spec or {}
    permissions = dict(spec.get('tool_permission') or {})
    deny = [str(n) for n in (spec.get('tools.deny') or [])]
    allow = [str(n) for n in (spec.get('tools.allow') or [])]
    instruction = str(spec.get('system_prompt') or '')
    return ModeSpec(name, instruction, permissions, deny, allow)


def resolve_mode(config: Config) -> tuple[ModeSpec, list[str]]:
    name = str(config.get('mode') or 'build')
    specs = {str(k): v for k, v in (config.get('modes') or {}).items()}
    if name not in specs:
        name = 'build'
    return _normalize_spec(name, specs.get(name) or {}), sorted(specs)


def mode_list(config: Config) -> list[ModeSpec]:
    specs = {str(k): v for k, v in (config.get('modes') or {}).items()}
    return [_normalize_spec(n, s) for n, s in sorted(specs.items())]


def merge_policy(config: Config) -> tuple[dict, list, list]:
    mode, _ = resolve_mode(config)
    permissions = dict(config.get('tool_permission') or {})
    permissions.update(mode.permissions)
    deny = [str(n) for n in (config.get('tools.deny') or [])] + mode.deny
    allow = mode.allow if mode.allow else [str(n) for n in (config.get('tools.allow') or [])]
    return permissions, allow, deny


def system_instruction(config: Config) -> str:
    parts = []
    system_prompt = config.get('system_prompt')
    if system_prompt:
        parts.append(str(system_prompt))
    mode, _ = resolve_mode(config)
    if mode.instruction:
        parts.append(mode.instruction)
    return '\n\n'.join(parts).strip()