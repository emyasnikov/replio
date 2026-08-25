from pathlib import Path


class ToolPolicy:
    def __init__(self, permissions: dict, allow: list | None = None,
                 deny: list | None = None, worktree: Path | None = None,
                 resolvers: dict | None = None):
        self.permissions = dict(permissions or {})
        self.allow = set(allow or [])
        self.deny = set(deny or [])
        self.worktree = worktree.resolve() if worktree else None
        self.resolvers = dict(resolvers or {})

    def _base_action(self, name: str, permission_key: str) -> str:
        if name in self.deny:
            return 'deny'
        if self.allow and name not in self.allow:
            return 'deny'
        action = self.permissions.get(permission_key, 'ask')
        return action if action in ('allow', 'ask', 'deny') else 'ask'

    def _outside_worktree(self, path: str) -> bool:
        if not self.worktree:
            return False
        try:
            p = Path(path).expanduser().resolve()
        except OSError:
            return True
        try:
            return not p.is_relative_to(self.worktree)
        except OSError:
            return True

    def action(self, name: str, permission_key: str,
               path: str | None = None, args: dict | None = None) -> str:
        action = self._base_action(name, permission_key)
        if action != 'deny' and args is not None:
            resolver = self.resolvers.get(name)
            if resolver is not None:
                try:
                    resolved = resolver(args)
                except Exception:
                    resolved = None
                if resolved in ('allow', 'ask', 'deny'):
                    action = resolved
        if action == 'allow' and path and self._outside_worktree(path):
            return 'ask'
        return action

    def allowed(self, name: str, permission_key: str | None = None) -> bool:
        if name in self.deny or (self.allow and name not in self.allow):
            return False
        if permission_key:
            return self.action(name, permission_key) != 'deny'
        return True

    def needs_confirm(self, name: str, permission_key: str,
                      path: str | None = None) -> bool:
        return self.action(name, permission_key, path) == 'ask'
