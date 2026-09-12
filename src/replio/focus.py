from __future__ import annotations

from .engine import Engine


class FocusManager:
    def __init__(self, root: Engine):
        self.root = root
        self._stack: list[Engine] = [root]
        self._engines: dict[str, Engine] = {}

    @property
    def active(self) -> Engine:
        return self._stack[-1]

    def stack(self) -> list[Engine]:
        return list(self._stack)

    def engines(self) -> list[Engine]:
        return [self.root] + list(self._engines.values())

    def is_root(self) -> bool:
        return self.active is self.root

    def find(self, role: str) -> Engine | None:
        for engine in self.engines():
            if engine.role == role:
                return engine
        return None

    def enter(self, engine: Engine) -> Engine:
        if engine is not self.active:
            self._stack.append(engine)
        self._repoint(self.active)
        return self.active

    def focus_role(self, role: str) -> Engine:
        role = str(role or '').strip()
        if not role or role == self.root.role:
            return self.reset()
        engine = self._engines.get(role)
        if engine is None:
            engine = self.root.focused_engine(
                role, ui=getattr(self.root, '_ui', None))
            self._engines[role] = engine
        return self.enter(engine)

    def back(self) -> Engine:
        if len(self._stack) > 1:
            self._stack.pop()
        self._repoint(self.active)
        return self.active

    def reset(self) -> Engine:
        self._stack = [self.root]
        self._repoint(self.root)
        return self.root

    def _repoint(self, engine: Engine):
        ui = getattr(self.root, '_ui', None)
        if ui is not None and hasattr(ui, '_loop'):
            ui._loop = engine
