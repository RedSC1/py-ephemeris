"""Immutable Shen Sha modules backed by the C++ BaZi catalog."""
from dataclasses import dataclass
from typing import Callable, Optional, Tuple
from . import _bazi_native as _native  # pyright: ignore[reportAttributeAccessIssue]
from . import _chart, BaziGender, BaziShenShaTargetKind


@dataclass(frozen=True)
class BaziShenShaInput:
    """Packed Ganzhi bytes; unknown hour is 0xff, never a fabricated hour."""
    pillars: Tuple[int, int, int, int]
    target: int
    target_kind: BaziShenShaTargetKind
    gender: Optional[BaziGender]


@dataclass(frozen=True)
class BaziShenShaRule:
    id: str
    name: str
    test: Callable[[BaziShenShaInput], bool]


@dataclass(frozen=True)
class BaziShenShaModule:
    label: str
    rules: Tuple[BaziShenShaRule, ...]

    def __post_init__(self):
        object.__setattr__(self, "rules", tuple(self.rules))


@dataclass(frozen=True)
class BaziShenShaMatch:
    id: str
    name: str
    builtin_id: Optional[int]


def _predicate(rule):
    if not callable(rule.test):
        raise TypeError("test must be callable")
    callback = rule.test

    def invoke(pillars, target, kind, gender):
        return callback(BaziShenShaInput(tuple(pillars), target,
            BaziShenShaTargetKind(kind), None if gender == -1 else BaziGender(gender)))
    return invoke


class _ShenShaHandle:
    def _require_native(self):
        native = self._native
        if native is None:
            raise RuntimeError("Shen Sha handle is closed")
        return native

    @property
    def is_closed(self):
        return self._native is None

    def close(self):
        """Release this snapshot, including native-held callback references.

        Existing derived snapshots stay valid. An evaluation already running
        retains its own reference until it returns; subsequent calls fail.
        """
        self._native = None

    def __enter__(self):
        self._require_native()
        return self

    def __exit__(self, *_):
        self.close()


class BaziShenShaCatalog(_ShenShaHandle):
    """An immutable catalog. Built-ins cannot be replaced or removed."""
    def __init__(self):
        self._native = _native.NativeShenShaCatalog()

    @classmethod
    def _wrap(cls, native):
        instance = cls.__new__(cls)
        instance._native = native
        return instance

    def add_module(self, module):
        return self._wrap(self._require_native().add_module(module.label, [
            dict(id=rule.id, name=rule.name, test=_predicate(rule)) for rule in module.rules]))

    def remove_module(self, label):
        """Remove all rules in a user module; existing snapshots stay valid."""
        return self._wrap(self._require_native().remove_module(label))

    def create_context(self, *, disabled_ids=()):
        return BaziShenShaContext(self._require_native().create_context(list(disabled_ids)))


class BaziShenShaContext(_ShenShaHandle):
    """Owns a native snapshot and callback references; supports close/with.

    Evaluations retain the GIL. Callback exceptions propagate unchanged. This
    does not make mutable objects captured by user callbacks thread-safe.
    Use close/with when callbacks capture this handle or an owner of it:
    Python GC cannot see references held inside the native snapshot.
    """
    def __init__(self, native):
        self._native = native

    def evaluate(self, chart, target, target_kind, *, gender=None):
        native = self._require_native()
        values = native.evaluate(_chart(chart), target.raw, target_kind.value,
            -1 if gender is None else gender.value)
        return tuple(BaziShenShaMatch(key, name, None if builtin == -1 else builtin)
                     for key, name, builtin in values)
